import requests, json, os, time, sys, getopt

EXT_PROPERTIES=".properties"
EXT_SQL=".sql"
EXT_ZIP=".zip"

def main(argv):

    ################# GET THE ARGS #######################
    opts, args = getopt.getopt(argv,"he:u:a:b:",["env-name=","env-url=","api-key=", "base-path="])
    for opt, arg in opts:
        if opt == '-h':
            print ("help goes here")
            sys.exit()
        elif opt in ("-e", "--env-name"):
            env_name = arg
        elif opt in ("-u", "--env-url"):
            env_url = arg
        elif opt in ("-a", "--api-key"):
            api_key = arg
        elif opt in ("-b", "--base-path"):
            base_path = arg

    ################# SET THE VARS #######################
    insp_ep=env_url+"/suite/deployment-management/v1/inspections"
    dep_ep=env_url+"/suite/deployment-management/v1/deployments"
    release_name= json.load(open(base_path + '/deployment_config.json'))["release_name"]
    ds_name= json.load(open(base_path + '/deployment_config.json'))["ds_name"]
    artifact_path= base_path + '/deployable_artifact/' + release_name

    ################# SET THE ARTIFACTS #######################
    
    pkg_filename=""
    prop_filename=""
    sql_filenames=  get_files_from_folder(artifact_path, EXT_SQL)

    if(len(get_files_from_folder(artifact_path, EXT_ZIP))):
        pkg_filename = get_files_from_folder(artifact_path, EXT_ZIP)[0]
    else:
        print("TODO - throw error")

    if(len(get_files_from_folder(artifact_path, env_name + EXT_PROPERTIES))):
        prop_filename = get_files_from_folder(artifact_path, env_name + EXT_PROPERTIES)[0]
    else:
        print("TODO - throw error")
    
   
    print("\n################# PRING SUMMARY #######################")
    print("Preparing the release - "+ release_name)
    print("Env Name - " + env_name)
    print("Env URL - " + env_url)
    print("Datasource name - " + ds_name)
    print("Artifact path is - " + artifact_path)
    print("Package file name - " + pkg_filename)
    print("Properties file name - " + prop_filename)
    print("SQL files are - ")
    print(sql_filenames)
    print("\n")
    print("\n################# START INSPECTION #######################")
    
    start_inspection_res_json = start_inspection(artifact_path, insp_ep, api_key, pkg_filename, prop_filename)
    print("\n")
    print(start_inspection_res_json)

    print("\n################# CHECK INSPECTION STATUS #######################")
    
    get_inspection_status_json = get_status(start_inspection_res_json["url"], api_key)
    print("\n")
    print(get_inspection_status_json["status"])
    print("\n")
    
    while(get_inspection_status_json["status"] == "IN_PROGRESS"):
        print("Inspection in progress...")
        time.sleep(1)
        get_inspection_status_json = get_status(start_inspection_res_json["url"], api_key)
    
    total_errors =  get_inspection_status_json["summary"]["problems"]["totalErrors"]

    print("\n################# EXIST ON ERRORS #######################")
    
    if(total_errors > 0 ):
        print(get_inspection_status_json)
        exit("Error occured...")

    print("\n################# START DEPLOYMENT #######################")
    
    get_deploy_status_json = start_deployment(artifact_path, dep_ep, api_key, pkg_filename, prop_filename, sql_filenames, release_name, ds_name)
    print("\n")
    print(get_deploy_status_json )
    print("\n")
    
    print("\n################# CHECK DEPLOYMENT STATUS #######################")
    
    deployment_status_check_url=get_deploy_status_json["url"]

    while(get_deploy_status_json["status"] == "IN_PROGRESS" or get_deploy_status_json["status"] == "PENDING_REVIEW" ):
        print("Deployment in progress...")
        time.sleep(1)
        get_deploy_status_json = get_status(deployment_status_check_url, api_key)
        print(get_deploy_status_json)
      
    print(get_deploy_status_json["summary"]["deploymentLogUrl"])
 
    print("\n################# PRINT DEPLOYMENT LOGS #######################")
    
    print(get_deployment_logs(get_deploy_status_json["summary"]["deploymentLogUrl"], api_key))

############## START INSPECTION ######################
def start_inspection(artifact_path, insp_url, api_key, pkg_filename, prop_filename):
    request_headers = {
        "Appian-API-Key": api_key
    }
    
    form_json = {}
    form_json['packageFileName'] = pkg_filename
    if(prop_filename!=""):
        form_json['customizationFileName'] = prop_filename

    form_data = {
        'json': (None, json.dumps(form_json)),
        'zipFile' : open(artifact_path + "/" + pkg_filename,'rb')
    }
    if(prop_filename!=""):
        form_data['ICF'] = open(artifact_path + "/" + prop_filename ,'rb')
    
    print(form_data)
    response = requests.post(
        url=insp_url,
        headers=request_headers,
        files=form_data
    )
    json_obj = json.loads(response.content)
    return  json_obj
    

############## GET STATUS ######################
def get_status(url, api_key):
    request_headers = {
        "Appian-API-Key": api_key
    }
    
    response = requests.get(
        url = url,
        headers=request_headers
    )

    json_obj = json.loads(response.content)
    return  json_obj


############## START DEPLOYMENT ######################
def start_deployment(artifact_path, dep_ep, api_key, pkg_filename, prop_filename, sql_filenames, release_name, ds_name):
    request_headers = {
        "Appian-API-Key": api_key
    }
    form_json={
        "name": release_name,
        "description": "Base functionality for " + release_name,
        "packageFileName": pkg_filename,
        "dataSource": ds_name
    }
    print(prop_filename)
    
    if(prop_filename!=""):
        form_json['customizationFileName'] = prop_filename
    index=0
    
    print(sql_filenames)
    
    if(len(sql_filenames)):
        form_json["databaseScripts"]=[]    
    sql_json=[]
    for sql_file in sql_filenames:
        form_json["databaseScripts"].append({
            "fileName": sql_file,
            "orderId": index+1
        })
        index = index + 1
    print(form_json)


    form_data = {
        'json': (None, json.dumps(form_json)),
        'zipFile' : open(artifact_path + "/" + pkg_filename,'rb')
    }
    if(prop_filename!=""):
        form_data['ICF'] = open(artifact_path + "/" + prop_filename ,'rb')
    
    index=0
    for sql_file in sql_filenames:
        form_data['sql'+ str(index)] = open(artifact_path + "/" + sql_file ,'rb')
        index=index+1

    print(form_data)

    response = requests.post(
        url=dep_ep,
        headers=request_headers,
        files=form_data
    )
    json_obj = json.loads(response.content)
    return  json_obj


############## GET DEPLOYMENT LOGS ######################
def get_deployment_logs(url, api_key):
    request_headers = {
        "Appian-API-Key": api_key
    }
    
    response = requests.get(
        url = url,
        headers=request_headers
    )
    return  response.content


############## UTILS ######################
def pretty_print_POST(req):
    
    print('{}\n{}\r\n{}\r\n\r\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
    ))

def get_files_from_folder(base_folder, ext):
    
    res = []

    for path in os.listdir(base_folder):
        # check if current path is a file
        if os.path.isfile(os.path.join(base_folder, path)):
            if(ext==""):
                res.append(path)
            elif (path.endswith(ext)):
                res.append(path)
    return res


if __name__ == "__main__":
   main(sys.argv[1:])

