import requests

#getting running spiders
jobs = requests.get('http://localhost:6800/listjobs.json?project=BlogCrawler').json()
running_spiders = [x['spider'] for x in jobs['running']]

#getting all spiders
print("---- Starting Spiders ----")
response = requests.get("http://localhost:6800/listspiders.json?project=BlogCrawler").json()
for spider in response['spiders']:
    if spider not in running_spiders:
        payload = {"project":"BlogCrawler", "spider":spider}
        r = requests.post("http://localhost:6800/schedule.json", data=payload)
        print(f"{spider}: {r}")
