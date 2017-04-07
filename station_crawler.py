# coding: utf-8
#---------------------------------------------------------------
# 気象観測所リストの取得
#---------------------------------------------------------------
import sys
import os
import csv
import time
import datetime
import dateutil
import urllib
import lxml.html
import re

ACCESS_INTERVAL = 3 # サーバー負荷考慮 seconds. 

#---------------------------------------------------------------
# 文字コード変換
def convert_encoding(data, to_enc="utf_8"):
  lookup = ('utf_8', 'euc_jp', 'euc_jis_2004', 'euc_jisx0213',
    'shift_jis', 'shift_jis_2004','shift_jisx0213',
    'iso2022jp', 'iso2022_jp_1', 'iso2022_jp_2', 'iso2022_jp_3',
    'iso2022_jp_ext','latin_1', 'ascii')
  
  for encoding in lookup:
    try:
      data = data.decode(encoding)
      break
    except:
      pass
  if isinstance(data, unicode):
    return data.encode(to_enc)
  else:
    return data

#---------------------------------------------------------------
# 都道府県・振興局リスト取得
def get_prec_numbers():
  prec_numbers = []
  URL = "http://www.data.jma.go.jp/obd/stats/etrn/select/prefecture00.php"
  xml = urllib.urlopen(URL).read().decode("utf-8")
  tree = lxml.html.fromstring(xml)
  
  repattern = re.compile(r"prec_no=(\d\d)")
  
  areas = tree.cssselect("area")
  for area in areas:
    s = repattern.search(area.get("href"))
    prec_numbers.append(s.group(1))
  
  return prec_numbers

#---------------------------------------------------------------
# 観測所リスト取得
def get_stations(prec_no):
  stations = []
  already_appended = {}
  URL = "http://www.data.jma.go.jp/obd/stats/etrn/select/prefecture.php?prec_no=" + prec_no
  xml = urllib.urlopen(URL).read().decode("utf-8")
  tree = lxml.html.fromstring(xml)
  
  re_block_no = re.compile(r"block_no=(\d{4,5})")
  re_attrs = re.compile(r"\((.+)\)")
  
  areas = tree.cssselect("area")
  for area in areas:
    href = area.get("href")
    search_block = re_block_no.search(href)
    if search_block == None: # 他都道府県・振興局へのリンク
      continue
    
    block_no = search_block.group(1)
    onmouseover = area.get("onmouseover")
    search_attrs = re_attrs.search(onmouseover)
    attrs = search_attrs.group(1).replace('\'', '').split(",") # 'a','1207','船泊','フナドマリ','45','26.2','141','02.1','8','1','1','1','1','0','2003','10','16','','','','',''
    measure_end_year = int(attrs[14])
    if (measure_end_year < 2999):
      end_date = datetime.date(int(attrs[14]), int(attrs[15]), int(attrs[16])) # 観測終了日
    else:
      end_date = None # 観測終了日
    
    station_code = attrs[1]
    if not station_code in already_appended:
      station = {
        "prec_no": prec_no, # 都道府県・振興局番号
        "type": attrs[0], # 's'(国際地点番号、気象庁観測所) or 'a'(国内地点番号)
        "code": attrs[1], # 観測所コード(地点コード。観測所番号ではないので注意)
        "name": attrs[2], # 漢字名
        "kana": attrs[3], # カナ
        "latitude": int(attrs[4]) + float(attrs[5]) / 60, # 緯度
        "longitude": int(attrs[6]) + float(attrs[7]) / 60, # 経度
        "elevation": attrs[8], # 標高
        "precipitation_flg" : attrs[9], # 降水量観測フラグ
        "wind_flg" : attrs[10], # 風力・風向観測フラグ
        "temprature_flg" : attrs[11], # 気温観測フラグ
        "solar_flg": attrs[12], # 日射量観測フラグ
        "snow_flg": attrs[13], # 降雪・積雪量観測フラグ
        "end_date": end_date # 観測終了日
      }
      
      stations.append(station)
      already_appended[station_code] = True
  
  return stations

#---------------------------------------------------------------
# 観測所をCSV出力
def stations_to_csv(stations):
  path = os.path.join(os.getcwd(), 'stations.csv')
  f = open(path, "w")
  csv_writer = csv.writer(f, lineterminator='\n')
  
  csv_writer.writerow([
    '都道府県・振興局番号',
    '種別',
    '地点番号',
    '地点名',
    '地点名カナ',
    '緯度',
    '経度',
    '標高',
    '降水量',
    '風',
    '気温',
    '日照',
    '雪',
    '観測終了日'
  ])
  
  for station in stations:
    csv_writer.writerow([
      station["prec_no"],
      station["type"],
      station["code"],
      convert_encoding(station["name"]),
      convert_encoding(station["kana"]),
      '%.5f' % (station["latitude"]), # 精度約1メートルまで考慮
      '%.5f' % (station["longitude"]), # 精度約1メートルまで考慮
      station["elevation"],
      station["precipitation_flg"],
      station["wind_flg"],
      station["temprature_flg"],
      station["solar_flg"],
      station["snow_flg"],
      station["end_date"]
    ])
  
  f.close()

#---------------------------------------------------------------
if __name__ == "__main__":
  prec_numbers = get_prec_numbers()
  
  all_stations = []
  for prec_number in prec_numbers:
    print '都道府県・振興局:' + prec_number
    stations = get_stations(prec_number)
    print '観測所数:'  + str(len(stations))
    all_stations.extend(stations)
    time.sleep(ACCESS_INTERVAL) # サーバー負荷考慮
    
  stations_to_csv(all_stations)
