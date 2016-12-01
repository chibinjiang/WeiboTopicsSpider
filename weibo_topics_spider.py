#coding=utf-8
import re
import json
import random
import requests
from datetime import datetime as dt
from bs4 import BeautifulSoup as bs
from requests.exceptions import (
    ProxyError,
    Timeout,
    ConnectionError,
    ConnectTimeout,
)
from abuyun_proxy import gen_abuyun_proxy
from config import MAIL_CURL_DICT, WEIBO_ACCOUNT
from utils import chin_num2dec, extract_cookie_from_curl
from decrators import retry, catch_network_error

EXC_LIST = (IndexError, KeyError, ProxyError, Timeout, ConnectTimeout, ConnectionError, Exception)


@catch_network_error(EXC_LIST)
@retry(EXC_LIST, tries=3)
def extract_topic_info(topic_uri):
    """
    Given topic url, parse HTML code and get topic info
    """
    info_dict = {}
    rand_account = WEIBO_ACCOUNT[random.randint(0, len(MAIL_CURL_DICT)-1)]
    curl_str = MAIL_CURL_DICT[rand_account].format(topic_uri=topic_uri)
    _, cookie = extract_cookie_from_curl(curl_str)
    if not cookie:
        return info_dict
    aby_proxy = gen_abuyun_proxy()
    r = requests.get(topic_uri, timeout=10, proxies={}, cookies=cookie)
    parser = bs(r.text, 'html.parser')
    if len(r.text) < 10000 or parser.find('div', {'class': 'W_error_bg'}):
        print >>open('access_error_%s.html' % dt.now().strftime("%Y-%m-%d %H:%M:%S"), 'w'), parser
        raise ConnectionError('Hey, boy, account %s was freezed' % rand_account)
    
    image_url_parser = None; stat_nums_parser = None; guide_parser = None; about_parser = None
    for script in parser.find_all('script'):
        script_text = script.text
        if 'pf_head S_bg2 S_line1' in script_text:
            image_url_parser = bs(json.loads(script.text[8:-1])['html'], 'html.parser')
        elif 'PCD_counter' in script_text:
            stat_nums_parser = bs(json.loads(script.text[8:-1])['html'], 'html.parser')
        elif 'topic_PCD_guide' in script_text:
            guide_parser = bs(json.loads(script.text[8:-1])['html'], 'html.parser')
        elif 'Pl_Core_T5MultiText__31' in script_text:
            about_parser = bs(json.loads(script.text[8:-1])['html'], 'html.parser')
    # import ipdb; ipdb.set_trace()
    # extract image url
    if image_url_parser:
        div_tag = image_url_parser.find('div', {'class': 'pf_username clearfix'})
        if div_tag and div_tag.find('h1'):
            info_dict['title'] = div_tag.find('h1').get('title', '').strip()[1:-1]  # remove # sign
        div_tag = image_url_parser.find('div', {'class': 'pf_head S_bg2 S_line1'})
        if div_tag and div_tag.find('img'):
            info_dict['image_url'] = div_tag.find('img').get('src')
    # extract the numbers of read, discuss, and fans
    if stat_nums_parser:
        div_tag = stat_nums_parser.find('div', {'class': 'PCD_counter'})
        if div_tag and len(div_tag.find_all(attrs={'class': re.compile(r'W_f')})) == 3:  # span or strong
            # info_dict['read_num'] = chin_num2dec(div_tag.find_all(attrs={'class': re.compile(r'W_f')})[0].text)
            info_dict['read_num'] = div_tag.find_all(attrs={'class': re.compile(r'W_f')})[0].text.strip()
            info_dict['dis_num'] = div_tag.find_all(attrs={'class': re.compile(r'W_f')})[1].text.strip()
            info_dict['fans_num'] = div_tag.find_all(attrs={'class': re.compile(r'W_f')})[2].text.strip()
            info_dict['read_num_dec'] = chin_num2dec(info_dict['read_num'])
    # extract guide article
    if guide_parser:
        div_tag = guide_parser.find('div', {'class': 'topic_PCD_guide'})
        if div_tag and div_tag.find('p', {'class': re.compile(r'W_f')}):
            info_dict['guide'] = div_tag.find('p', {'class': re.compile(r'W_f')}).text.strip()
    # extract type, label, and region of topic
    # import ipdb; ipdb.set_trace()
    if about_parser:
        for li_tag in about_parser.find_all('li'):
            title_tag = li_tag.find(attrs={'class': re.compile('pt_title')})
            detail_tag = li_tag.find(attrs={'class': re.compile('pt_detail')})
            title = title_tag.text.encode('utf8')
            if '分类' in title:  # http://weibo.com/3238362920/about
                info_dict['type'] = ' '.join([a_tag.text.strip() for a_tag in detail_tag.find_all('a')])
            elif '地区' in title:
                info_dict['region'] = ' '.join([a_tag.text.strip() for a_tag in detail_tag.find_all('a')])
            elif '标签' in title:
                info_dict['label'] = ' '.join([a_tag.text.strip() for a_tag in detail_tag.find_all('a')])
            else:
                print >>open('Other_unknown_attr_%s.html' % dt.now().strftime("%Y-%m-%d %H:%M:%S"), 'w'), about_parser
    if info_dict['guide'] and info_dict['image_url']:  # can't be none
        info_dict['access_time'] = dt.now().strftime('%Y-%m-%d %H:%M:%S')
        info_dict['topic_url'] = topic_uri
    return info_dict

def test_extract_topic_info():
    print 'test case 1'
    for key, value in extract_topic_info('http://weibo.com/p/100808d9d36d82afccaa73f80e8ef9c11c2c17').items():
        print key, value
    print 'test case 2'
    for key, value in extract_topic_info('http://weibo.com/p/10080890d8e011e4d65f67a67cf9acdc23a18e').items():
        print key, value


# test_extract_topic_info()