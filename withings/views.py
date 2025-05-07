from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import urlencode

from rest_framework import permissions, viewsets

from withings.serializers import UserInfoSerializer, DeviceSerializer, ExperimentSerializer, RawdataRecordSerializer
from withings.models import UserInfo, Device, Experiment, RawdataRecord

import json
import requests
import datetime as dt
from zoneinfo import ZoneInfo
import tzlocal

# Create your views here.


DT_ACCEL=1 # accelerometer data_type = 1

context_root = settings.WITHINGS_CONTEXT_ROOT + '/'
client_id = settings.WITHINGS_CLIENT_ID
client_secret = settings.WITHINGS_CLIENT_SECRET
redirect_uri = settings.WITHINGS_REDIRECT_URI


def get_access_token(userid):
    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        raise Exception("userid %s doesn't exist" % userid)
    
    return users[0].access_token

def get_deviceid(access_token):
    url = 'https://wbsapi.withings.net/v2/user'

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {'action': 'getdevice'}

    res = requests.post(url, urlencode(params), headers=headers)
    return res
    

def rawdata_activate(access_token, hash_deviceid, data_type, end_ts):
    url = 'https://wbsapi.withings.net/v2/rawdata'

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {"action": "activate", "hash_deviceid": hash_deviceid, "rawdata_type":data_type, "enddate": end_ts}

    res = requests.post(url, urlencode(params), headers=headers)
    return res



@csrf_exempt
def callback2(request):
    if request.method == "POST" or request.method == 'HEAD' or not request.GET.get('code'):
        return HttpResponse("CSSM PAHP Callback")
    code = request.GET.get('code')

    """
    Now, use this code to get access_token
    """

    url ='https://wbsapi.withings.net/v2/oauth2'
    params = {
            'action':'requesttoken',
            'grant_type':'authorization_code',
            'client_id':client_id,
            'client_secret':client_secret,
            'code':code,
            'redirect_uri':redirect_uri
            }

    data = {}
    res = requests.post(url, urlencode(params))
    res_json= res.json()

    json_body = res_json['body']
    userid = json_body["userid"]
    users = UserInfo.objects.filter(userid = userid)

    access_token = json_body["access_token"]


    

    if users.count() <= 0:
        new_user = UserInfo(**json_body)
        new_user.save()
    elif users[0].access_token != access_token:
        user = users[0]
        user.access_token = access_token
        user.refresh_token = json_body["refresh_token"]
        user.scope = json_body["scope"]
        user.expires_in = json_body["expires_in"]
        user.csrf_token = json_body["csrf_token"]
        user.token_type = json_body["token_type"]
        user.save()

    #return JsonResponse(res_json)
    return redirect('/' + context_root + "experiments/")




@csrf_exempt
def notifyCallback(request):
    """
    For getting callback if subscribe to 'withings notify' (not implemented yet, 03/04/2025)
    """
    if request.method == 'POST':
        try:
            # Decode the request body and load JSON
            body_unicode = request.body.decode('utf-8')
            data = json.loads(body_unicode)
            
            now = dt.datetime.now()
            filename = "withings_notify_%s.json" % int(now.timestamp())

            # Write the JSON data to a file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            return JsonResponse({'status': 'success', 'message': 'notificaiton saved.'})
        
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

        
def activate(request):
    required_params = ['userid', 'endtime']
    for param in required_params:
        if not request.GET.get(param):
            return HttpResponse("Missing parameter: " + param, 400)
    userid = request.GET['userid']
    #hash_deviceid = request.GET['hdeviceid']
    #data_type = request.GET['dtype']

    endtime = request.GET['endtime']
    et = dt.datetime.strptime(endtime, "%Y-%m-%dT%H:%M")
    est = et.replace(tzinfo=ZoneInfo(tzlocal.get_localzone_name()))
    enddate = int(est.timestamp())

    data_type = 1 # Accelerometer data

    devices = Device.objects.filter(userid=userid)
    if devices.count() <= 0:
        return JsonResponse({"error": "no device associated with userid:%s" % userid})

    hash_deviceid = devices[0].hash_deviceid

    startdate = int(dt.datetime.now().timestamp())

    exps = Experiment.objects.filter(hash_deviceid=hash_deviceid, enddate__gt=startdate)
    if exps.count() > 0:
        return JsonResponse({"error": "an existing experiment ends at %s" % exps[0].enddate})

    access_token = get_access_token(userid)
    res = rawdata_activate(access_token, hash_deviceid, data_type, enddate)

    res_json = res.json()
    if res_json['status'] == 0:
        """
        Write an experiment record
        """
        e = Experiment(hash_deviceid=hash_deviceid, userid=userid, startdate=startdate, enddate=enddate)
        e.save()
    else:
        return JsonResponse({"error":"access token experied"})

    return redirect('/' + context_root + "experiments/")

def getdevices(request):
    userid = request.GET['userid']
    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        return JsonResponse({"error": "userid %s doesn't exist" % userid})
    
    access_token = users[0].access_token

    res = get_deviceid(access_token)
    res_json = res.json()
    devices = res_json["body"]["devices"]
    
    for d in devices:
        target_devices = Device.objects.filter(deviceid=d['deviceid'], userid=userid)
        if target_devices.count() <= 0:
            new_device = Device(hash_deviceid=d['hash_deviceid'],userid=userid)
            new_device.deviceid = d['deviceid']
            new_device.mac_address = d['mac_address']
            new_device.type = d['type']
            new_device.model = d['model']
            new_device.mode_id = d['model_id']
            new_device.timezone = d['timezone']
            new_device.fw = d['fw']
            new_device.first_session_date = d['first_session_date']
            new_device.last_session_date = d['last_session_date']

            new_device.save()

    return JsonResponse(res_json)

def activate_sensor(userid, hash_deviceid, sensor_type, end_ts):
    """
    Activate rawdata sensor logging now (immediately)
    """

    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        return JsonResponse({'error': "userid %s doesn't exist" % userid})
    
    access_token = users[0].access_token
    res = rawdata_activate(access_token, hash_deviceid, sensor_type, end_ts)
    
    return JsonResponse(res.json())

from .utils import rawdata2dfs, write2csv, write2json

def get_rawdata(request):
    exp_id = request.GET['exp_id']
    offset = request.GET.get("offset")

    exps = Experiment.objects.filter(id=exp_id)
    if exps.count() <= 0:
        return JsonResponse({"error": "exp_id %s does not exist." % exp_id})
    
    exp = exps[0]
    userid = exp.userid
    hash_deviceid = exp.hash_deviceid
    rawdata_type = 1
    startdate = exp.startdate
    enddate = exp.enddate

    """
    Design: 
    1. We need to pull the data multiple times and write the data into csv files.
    2. We need to save the filenames into a database for retrieving purposes. We need to create a 
    model for this database.
    """

    url = 'https://wbsapi.withings.net/v2/rawdata'
    params = {
        'action': 'get', 'hash_deviceid':hash_deviceid, 'rawdata_type':rawdata_type,
        'startdate':startdate, 'enddate': enddate
        }
    
    if offset:
        params["offset"] = offset
    else:
        offset = 0

    access_token = get_access_token(userid)
    headers = {"Authorization": "Bearer %s" % access_token}
    res = requests.post(url, urlencode(params), headers=headers)    
    jres = res.json()

    file_path = settings.WORKING_WITHINGS_DATA_PATH

    # save the raw json file
    raw_filename = "raw_%s_%s_%s.json" % (startdate, enddate, offset)
    write2json(jres, file_path, raw_filename)

    # save to csv files
    rawdata = jres['body']['rawdata']
    dfs = rawdata2dfs(rawdata)
    for sensor_name in dfs:
        filename = "%s_%s_%s_%s.csv" % (sensor_name, startdate, enddate, offset)
        df = dfs[sensor_name]
        write2csv(df, file_path, filename)

        # write into FileRecord 
        rds = RawdataRecord.objects.filter(filename=filename)
        if rds.count() > 0:
            rds[0].filename = filename
            rds[0].save()
        else:
            rd = RawdataRecord(exp=exp, filename=filename)
            rd.save()

    if 'offset'in jres['body']:
        offset = jres['body']['offset']
        exp.download_offset = offset
        exp.save()
    else:
        exp.download_offset = -1
        exp.save()
    
    return redirect('/' + context_root + "experiments/")

def list_heart(request):
    userid = request.GET['userid']
    startdate = request.GET['startdate']
    enddate = request.GET['enddate']

    url = 'https://wbsapi.withings.net/v2/heart'
    access_token = get_access_token(userid)

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {'action':'list', 'startdate':startdate, 'enddate':enddate}


    res = requests.post(url, params, headers=headers)
    return JsonResponse(res.json())

def get_heart(request):
    userid = request.GET['userid']
    signalid = request.GET['signalid']

    url = 'https://wbsapi.withings.net/v2/heart'
    access_token = get_access_token(userid)

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {'action':'get', 'signalid':signalid}

    res = requests.post(url, params, headers=headers)
    return JsonResponse(res.json())


def oauth2(request):
    url = 'https://account.withings.com/oauth2_user/authorize2'
    params = {
                'response_type':'code',
                # dcp
                #'client_id':'b007216a30ef05a7460e943097f24a4057c019a5de35af805d2dcedafe406825',
                'client_id':client_id,
                # pahplabresearch1
                #'client_id':'feff00522ffdd5d90227173d55c4487861349473f070a4e52985910cfd878bf0',
                # south carolina
                #'client_id':'91eaaa60979afb77a65032a1b6019723351e6c5bde7827eb346de1c63aadb3ae',
                'scope':'user.info,user.metrics,user.activity,user.rawdata',
                'redirect_uri':redirect_uri,
                #'redirect_uri':'https://pahplab.cssm.iastate.edu/withings/callback/',
                #'redirect_uri':'http://withings.geosketch.art/callback/',
                'state':'VA'}
    
    oauth2_url = '%s?%s' % (url,urlencode(params))
    return redirect(oauth2_url)



class UserInfoViewSet(viewsets.ModelViewSet):
    queryset = UserInfo.objects.all()
    serializer_class = UserInfoSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


class ExperimentViewSet(viewsets.ModelViewSet):
    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer


class RawdataRecordViewSet(viewsets.ModelViewSet):
    queryset = RawdataRecord.objects.all()
    serializer_class = RawdataRecordSerializer


from .utils import timestamp2est

def withings_experiments(request):
    exps = Experiment.objects.all().order_by('-created')

    now_ts = dt.datetime.now().timestamp()

    exp_list = []
    for exp in exps:
        start_time = timestamp2est(exp.startdate)
        end_time = timestamp2est(exp.enddate)

        data_files = exp.rawdata_records.order_by('created')

        on_going = False
        if exp.enddate > now_ts:
            on_going = True

        record = {
            'id':exp.id, 'userid':exp.userid, 'start_time':str(start_time), 'end_time':str(end_time), 
            'data_files':data_files, 'offset':exp.download_offset, 'on_going':on_going
            }
        
        exp_list.append(record)

    return render(request, "withings_experiments.html", {'exp_list': exp_list, 'context_root': context_root})
