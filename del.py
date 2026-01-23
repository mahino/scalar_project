
for deployment in json.loads(response.content)['data']:
  sData = copy.deepcopy(sample_data)
  s = deployment
  for i in s['deployments']:  
    url = "https://rdm.eng.nutanix.com/api/v1/deployments/" + i['$oid']
    lol = requests.request("GET", url, headers=headers, verify=False)
    lol = json.loads(lol.content)
    if 'message' in lol and lol['message'] == "ScheduledDeployment does not exist":
      continue
    elif 'svm_ip' in lol['data']['allocated_resource']:
      sData['pe_ip'] = lol['data']['allocated_resource']['svm_ip']
    elif 'host' in lol['data']['allocated_resource']:
      sData['pc_ip'] = lol['data']['allocated_resource']['host']
  sData['cluster_name'] = s['payload']['name']
  sData['user_name'] = s['client']['owner']
  sData['pool'] = s['allocated_pool']
  for i in s['payload']['resource_specs']:
    if "nos" in i['software']:
      sData['pe_version'] = i['software']['nos']['version']
  data.append(sData)

print(json.dumps(data))

[{"pe_ip": "10.33.228.72", "pc_ip": "10.33.96.20", "cluster_name": "mohan_ncm", "user_name": "mohan.as1", "pool": "global_pool_physical_1", "pe_version": "ganges-7.5-stable"}, {"pe_ip": "10.117.65.78", "cluster_name": "PE_longevity", "user_name": "shashi.kiran", "pool": "ncm_st", "pe_version": "ganges-7.5-stable"}, {"pe_ip": "10.46.117.162", "cluster_name": "PE2_longevity", "user_name": "shashi.kiran", "pool": "ncm_st", "pe_version": "ganges-7.5-stable"}, {"pe_ip": "10.112.102.168", "cluster_name": "NCM2.0_longevity", "user_name": "shashi.kiran", "pool": "ncm_st", "pe_version": "ganges-7.5-stable"}, {"pe_ip": "10.46.117.108", "cluster_name": "PE1_longevity", "user_name": "shashi.kiran", "pool": "ncm_st", "pe_version": "ganges-7.5-stable"}, {"pe_ip": "10.46.209.101",
"pc_ip": "10.53.55.30", "cluster_name": "homepc_NCM2.0_longevity", "user_name": "shashi.kiran", "pool": "ncm_st", "pe_version": "ganges-7.5-stable"}]