import json, config #標準のjsonモジュールとconfig.pyの読み込み
from requests_oauthlib import OAuth1Session #OAuthのライブラリの読み込み
import requests, time, re

GET_TWEETS_NUM = 500
POST_NUM_IN_MSG = 1
POST_QPS = 3

CK = config.CONSUMER_KEY
CS = config.CONSUMER_SECRET
AT = config.ACCESS_TOKEN
ATS = config.ACCESS_TOKEN_SECRET

def get_tweets_by_listid(twitter, list_id, since_id):
  url = "https://api.twitter.com/1.1/lists/statuses.json" 
  params = {'count' : GET_TWEETS_NUM, 'list_id': list_id} 
  if since_id:
    params['since_id'] = since_id

  res = twitter.get(url, params = params)
  if res.status_code != 200:
    print("get_tweets_by_listid Failed: {}, {}".format(res.status_code, res.text))
    return False

  timelines = json.loads(res.text)

  # 古い方を先頭にする
  timelines.reverse() 
  return timelines

def get_tweet_by_id(twitter, id):
  url = "https://api.twitter.com/1.1/statuses/show.json" 
  params = {'id': id}

  res = twitter.get(url, params = params)
  if res.status_code != 200:
    print("get_tweeet_by_id Failed: {}, {}".format(res.status_code, res.text))
    return False
  return res.text

def get_lists(twitter):
  url = "https://api.twitter.com/1.1/lists/list.json"
  params = {'sreen_name': 'ebahy'}
  res = twitter.get(url, params = params)
  if res.status_code != 200:
    print("get_lists Failed: {}, {}".format(res.status_code, res.text))
    return False
  return [{'id': i['id_str'], 'full_name': i['full_name'].split('/')[1]} for i in json.loads(res.text)]


def read_settings():
  with open('settings.json') as f:
    df = json.load(f)
  return df

def write_settings(d):
  with open('settings.json', 'w') as f:
    df = json.dump(d, f, indent=4)


class Crawl:
  def __init__(self, twitter, setting):
    self.twitter = twitter
    self.since_id = setting['since_id'] if 'since_id' in setting else ''
    self.post_url = setting['post_url']

    self.type = setting['type']
    self.name = setting['name']
    if self.type == 'list':
      self.list_id = setting['list_id']
    elif self.type == 'search':
      self.search_word = setting['search_word']

  def get_tweets(self):
    if self.type == 'list':
      return get_tweets_by_listid(self.twitter, self.list_id, self.since_id)
    elif self.type == 'search':
      pass
    else:
      print("get_tweets Failed: invalid type", self.type)

  def make_post_data(self, tweets):
    def make_data(t):
      d = []
      if 'retweeted_status' in t:
        d.append('RT:')

      d.append(t['user']['name'])

      d.append('list({})'.format(self.name))

      d.append(t['created_at'])
       
      d = ['```fix\n### {} ```'.format(' '.join(d))] 
      
      url = 'https://twitter.com/{}/status/{}'.format(t['user']['screen_name'], t['id'])
      d.append(url)

      for u in t['entities']['urls']:
        if u['expanded_url'] == url:
          continue
        m = re.match(r'https://twitter.com/i/web/status/(.*)', u['expanded_url'])
        if m and m.group(1) == str(t['id']):
          continue
        d.append(u['expanded_url'])

      return ' '.join(d)

    d = '\n'.join([make_data(t) for t in tweets])
    # post_tweets Failed: 400, {"content": ["Must be 2000 or fewer in length."]}
    return d[:2000]

  def post_tweets(self, tweets):
    response = requests.post(self.post_url, { 'content': self.make_post_data(tweets) })
    if response.status_code != 204:
      print("post_tweets Failed: {}, {}".format(response.status_code, response.text))
      d = json.loads(response.text)
      w = int(d['retry_after']) // 1000 + 1
      return -1, w
    return tweets[-1]['id'], 0

  
twitter = OAuth1Session(CK, CS, AT, ATS)
settings = read_settings()

#a = get_tweet_by_id(twitter, '1299297261239762952')
#print(a)

# settings.jsonに乗っていない新規listを取得して、settingsに追加する
lists = get_lists(twitter)
for l in lists:
  if l['id'] in [c['list_id'] for c in settings]:
    continue
  settings.append({'list_id': l['id'], 'name': l['full_name'], 'post_url': config.DEFAULT_POST_URL, 'type': 'list'})

total = 0
for setting in settings:
  print('INFO: doing list {}'.format(setting['name']))

  c = Crawl(twitter, setting)
  tweets = c.get_tweets()

  while tweets:
    tmp = tweets[:POST_NUM_IN_MSG]

    last_id, waitsec = c.post_tweets(tmp)
    if last_id == -1:
      print('INFO: waiting {} sec'.format(waitsec))
      time.sleep(waitsec)
      continue

    total += len(tmp)
    print('INFO: post count {}'.format(total))

    # shift posted tweets
    tweets = tweets[POST_NUM_IN_MSG:]

    setting['since_id'] = last_id
    setting['since_at'] = tmp[-1]['created_at']
    write_settings(settings)
