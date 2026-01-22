import requests

url = "https://jarvis.eng.nutanix.com/api/v2/pools/65e7aebf4dd19254d2bcd4b5/node_details?_dc=1769077572727&page=1&start=0&limit=25"

payload = {}
headers = {}

response = requests.request("GET", url, headers=headers, data=payload, verify=False)

print(response.text)
