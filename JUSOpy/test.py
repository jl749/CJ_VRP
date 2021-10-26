import time
from urllib.parse import quote_plus, urlencode
from urllib.request import urlopen, Request
import json


def jusoAPI(keystr):
    url = 'http://www.juso.go.kr/addrlink/addrLinkApi.do'
    queryParams = '?' + urlencode(
        {quote_plus('currentPage'): '1', quote_plus('countPerPage'): '1', quote_plus('resultType'): 'json',
         quote_plus('keyword'): keystr, quote_plus('confmKey'): 'devU01TX0FVVEgyMDIxMTAwMjIzNDkxMzExMTcxNDg='})
    request = Request(url + queryParams)
    request.get_method = lambda: 'GET'  # default GET anyway
    response_body = urlopen(request).read()

    root_json = json.loads(response_body)
    total = root_json['results']['common']['totalCount']

    if total == '1':
        ad = root_json['results']['juso'][0]
        return ad['jibunAddr'], ad['roadAddr']  # ['detBdNmList']
    else:
        return None


TEST_LIST = ['경기도 화성시 장안면 매바위로366번길 8',
             '경기도 화성시 장안면 매바위로 347',
             '경기도 화성시 장안면 버들로 1232-4',
             '경기 화성시 장안면 무봉길 200-6',
             '경기도 화성시 장안면 소개무골길 66-10',
             '경기 화성시 장안면 돌서지길 96-27 204호',
             '경기 화성시 장안면 석포공단길 24-13 왼쪽 동 2층 사무실',
             '경기도 화성시 장안면 돌서지길 28-7',
             '경기도 화성시 장안면 석포리 529 경기도 화성시 장안면 버들 안길',
             '경기도 화성시 장안면 매바위로 376']

jibun = [None] * 10
road = [None] * 10

index = 0
for add in TEST_LIST:
    tmp = jusoAPI(add)
    if tmp is not None:
        jibun[index] = tmp[0]
        road[index] = tmp[1]
    else:
        arr = add.split()
        count = 1
        while len(arr[: -count]) > 3:
            key = " ".join(arr[: -count])
            tmp = jusoAPI(" ".join(arr[: -count]))
            if tmp is not None:
                jibun[index] = tmp[0]
                road[index] = tmp[1]
                break
            time.sleep(1)
            count += 1
    index += 1

print(jibun)
print(road)
