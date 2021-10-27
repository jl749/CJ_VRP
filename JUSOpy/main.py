from urllib.parse import quote_plus, urlencode
from urllib.request import urlopen, Request
import json


def jusoAPI(keystr):
    if '오산시' in keystr:
        return None
    key_list = list(keystr.split())
    for i in range(len(key_list), 3, -1):
        addr = ' '.join(key_list[:i])
        url = 'http://www.juso.go.kr/addrlink/addrLinkApi.do'
        queryParams = '?' + urlencode(
            {quote_plus('currentPage'): '1', quote_plus('countPerPage'): '1', quote_plus('resultType'): 'json',
             quote_plus('keyword'): addr, quote_plus('confmKey'): '...'})
        while True:
            try:
                request = Request(url + queryParams)
                request.get_method = lambda: 'GET'  # default GET anyway
                response_body = urlopen(request).read()
                break
            except:
                continue

        root_json = json.loads(response_body)
        total = root_json['results']['common']['totalCount']
        if total != '0':
            ad = root_json['results']['juso'][0]
            return ad['roadAddr']  # ['detBdNmList']
    return None
