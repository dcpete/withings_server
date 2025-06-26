from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import urlencode

from rest_framework import permissions, viewsets

from withings.serializers import UserInfoSerializer, DeviceSerializer, ExperimentSerializer, RawdataRecordSerializer
from withings.models import UserInfo, Device, Experiment, RawdataRecord

import urllib
import json
import requests
import datetime as dt
from zoneinfo import ZoneInfo
import pytz
import urllib.parse

# Create your views here.


DT_ACCEL=1 # accelerometer data_type = 1

context_root = settings.WITHINGS_CONTEXT_ROOT + '/'
client_id = settings.WITHINGS_CLIENT_ID
client_secret = settings.WITHINGS_CLIENT_SECRET
redirect_uri = settings.WITHINGS_REDIRECT_URI




# check if the token is expired and, if so, refresh the token if possible
def is_token_expired(userid):
    # get the user object for this userid
    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        return JsonResponse({"error": "userid %s does not exist" % userid})
    user = users[0]

    # required properties for token validation
    required_token_props = [
        'access_token',
        'refresh_token',
        'updated',
        'expires_in'
    ]
    # if any required prop is missing, then token is invalid (or expired, sure)
    for prop in required_token_props:
        if not getattr(user, prop):
            return True

    issued_at = user.updated
    expires_in = user.expires_in

    # get datetime objects for now and issued_at
    d_now = dt.datetime.now(dt.timezone.utc)
    d_issued = issued_at

    # calculate expiration times
    access_token_expires_in = int(expires_in)
    refresh_token_expires_in = 31556952
    time_since_token = abs(d_now - d_issued).seconds
    time_until_access_token_expires = access_token_expires_in - time_since_token
    time_until_refresh_token_expires = refresh_token_expires_in - time_since_token
    # if debugging, log the info
    if settings.DEBUG:
        print("access token expires in " + str(time_until_access_token_expires) + " seconds")
        print("refresh token expires in " + str(time_until_refresh_token_expires) + " seconds")

    # if access token is not expired, then not expired
    if time_until_access_token_expires > 0:
        return False
    # otherwise if possible, refresh the token
    elif time_until_refresh_token_expires > 0:
        oauth2_refresh(userid)
        return False
    # otherwise yes, it is expired
    else:
        return True




# get the access token for a userid
def get_access_token(userid):
    # if no user, return error
    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        return JsonResponse({"error": "userid %s does not exist" % userid})
    user = users[0]
    return user.access_token




def get_refresh_token(userid):
    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        return JsonResponse({"error": "userid %s does not exist" % userid})
    user = users[0]
    return user.refresh_token




def save_auth_info(response):
    # define auth info to save
    issued_at = dt.datetime.now(dt.timezone.utc).isoformat()
    json_props = [ 
        'userid', 
        'access_token', 
        'refresh_token', 
        'scope',
        'expires_in',
        'csrf_token',
        'token_type'
    ]

    # get the userid from the response
    res_json = response.json()
    json_body = res_json['body']
    userid = json_body["userid"]

    # look for users in the db with this userid
    users = UserInfo.objects.filter(userid = userid)
    # if no users are found, make one
    if users.count() <= 0:
        # add the base info from the json response
        new_user = UserInfo()
        # add the issued_at date for token expiration calculations
        for prop in json_props:
            setattr(new_user, prop, json_body[prop])
        new_user.created = str(issued_at)
        new_user.updated = str(issued_at)
        new_user.save()
    # Otherwise if a user is found, update it
    else:
        user = users[0]
        for prop in json_props:
            setattr(user, prop, json_body[prop])
        user.updated = str(issued_at)
        user.save()




# get all associated devices for a user
def get_deviceid(access_token):
    url = 'https://wbsapi.withings.net/v2/user'

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {'action': 'getdevice'}

    res = requests.post(url, urlencode(params), headers=headers)
    return res




# send a request to withings to register an experiment
def rawdata_activate(access_token, hash_deviceid, data_type, end_ts):
    url = 'https://wbsapi.withings.net/v2/rawdata'

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {"action": "activate", "hash_deviceid": hash_deviceid, "rawdata_type":data_type, "enddate": end_ts}

    res = requests.post(url, urlencode(params), headers=headers)
    return res




# callback2 is automatically requested from 'redirect_uri' after oauth2 application authorization
@csrf_exempt
def callback2(request):
    if request.method == "POST" or request.method == 'HEAD' or not request.GET.get('code'):
        return HttpResponse("Withings callback")
    
    
    # Withings API will send a 'code' that can be used to get tokens
    # access_token expires in 10800 seconds by default ('expires_in' in the response)
    # refresh_token expires in one year and can be used to get a new access_token

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

    res = requests.post(url, urlencode(params))
    res_json= res.json()

    json_body = res_json['body']
    userid = json_body["userid"]
    access_token = json_body["access_token"]
    
    # save or update this info in the database
    save_auth_info(res)

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
            new_device.model_id = d['model_id']
            new_device.timezone = d['timezone']
            new_device.fw = d['fw']
            new_device.first_session_date = d['first_session_date']
            new_device.last_session_date = d['last_session_date']
            new_device.friendlyname = "Withings Watch #" + str(Device.objects.count() + 1)

            new_device.save()
        else:
            device = target_devices[0]
            device.mac_address = d['mac_address']
            device.type = d['type']
            device.model = d['model']
            device.model_id = d['model_id']
            device.timezone = d['timezone']
            device.fw = d['fw']
            device.first_session_date = d['first_session_date']
            device.last_session_date = d['last_session_date']
            device.save()

    #return JsonResponse(res_json)
    return redirect('/' + context_root + "experiments")




# update device properties in the local database
def update_device(request):
    required_params = ['deviceid']
    for param in required_params:
        if not request.POST.get(param):
            return HttpResponse("Missing parameter: " + param, 400)
    deviceid = request.POST.get("deviceid")
    
    # currently only updating friendlyname
    update_params = ['friendlyname']
    
    # get device from the database
    devices = Device.objects.filter(deviceid=deviceid)
    if devices.count() <= 0:
        return JsonResponse({"error": "no such device " + deviceid})
    device = devices[0]
    
    # update the parameters
    for param in update_params:
        if request.POST.get(param):
            setattr(device, param, request.POST.get(param))
    device.save()

    # return to experiments page
    return redirect('/' + context_root + "experiments")




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




# start an experiment
def activate(request):
    required_params = ['deviceid', 'endtime']
    for param in required_params:
        if not request.POST.get(param):
            return HttpResponse("Missing parameter: " + param, 400)
    deviceid = request.POST.get('deviceid')
    endtime = request.POST.get('endtime')

    devices = Device.objects.filter(deviceid=deviceid)
    if devices.count() <= 0:
        return JsonResponse({"error": "no such device " + deviceid})
    device = devices[0]
    userid = device.userid
    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        return JsonResponse({"error": "userid " + userid + " does not exist"})
    if is_token_expired(userid):
        return oauth2(request)
    
    et = dt.datetime.strptime(endtime, "%Y-%m-%dT%H:%M")
    et_local = et.replace(tzinfo=ZoneInfo(settings.TIME_ZONE))
    enddate = int(et_local.timestamp())

    data_type = 1 # Accelerometer data

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

    return redirect('/' + context_root + "experiments")




# update the list of devices for all registered users
def getdevices(request):
    users = UserInfo.objects.all()
    if users.count() <= 0:
        return oauth2(request)
    
    for user in users:
        userid = user.userid
        if is_token_expired(userid):
            return oauth2(request)
        
        access_token = get_access_token(userid)

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
                new_device.friendlyname = "Withings Watch #" + str(Device.objects.count() + 1)

                new_device.save()

    return redirect('/' + context_root + "experiments")




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

    if is_token_expired(userid):
        return oauth2(request)
    access_token = get_access_token(userid)
    headers = {"Authorization": "Bearer %s" % access_token}
    res = requests.post(url, urlencode(params), headers=headers)    
    jres = res.json()

    file_path = settings.WORKING_WITHINGS_DATA_PATH

    # save the raw json file
    raw_filename = "raw_%s_%s_%s.json" % (startdate, enddate, offset)
    write2json(jres, file_path, raw_filename)

    # save to csv files
    if jres.get('body'):
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

    if jres.get('body') and 'offset'in jres['body']:
        offset = jres['body']['offset']
        exp.download_offset = offset
        exp.save()
    else:
        exp.download_offset = -1
        exp.save()
    
    return redirect('/' + context_root + "experiments")




def list_heart(request):
    startdate = request.GET['startdate']
    enddate = request.GET['enddate']

    url = 'https://wbsapi.withings.net/v2/heart'
    access_token = get_access_token(request)
    if not access_token:
        return oauth2(request)

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {'action':'list', 'startdate':startdate, 'enddate':enddate}


    res = requests.post(url, params, headers=headers)
    return JsonResponse(res.json())




def get_heart(request):
    signalid = request.GET['signalid']

    url = 'https://wbsapi.withings.net/v2/heart'
    access_token = get_access_token(request)
    if not access_token:
        return oauth2(request)

    headers = {"Authorization": "Bearer %s" % access_token}
    params = {'action':'get', 'signalid':signalid}

    res = requests.post(url, params, headers=headers)
    return JsonResponse(res.json())




def oauth2_refresh(userid):
    users = UserInfo.objects.filter(userid=userid)
    if users.count() <= 0:
        return JsonResponse({"error": "userid %s does not exist" % userid})
    user = users[0]
    url = 'https://wbsapi.withings.net/v2/oauth2'
    params = {
                'action':'requesttoken',
                'client_id':client_id,
                'client_secret':client_secret,
                'grant_type':'refresh_token',
                'refresh_token':user.refresh_token
            }
    
    res = requests.post(url, params)
    save_auth_info(res)




def get_oauth2_url(request):
    url = 'https://account.withings.com/oauth2_user/authorize2'
    params = {
                'response_type':'code',
                'client_id':client_id,
                'scope':'user.info,user.metrics,user.activity,user.rawdata',
                'redirect_uri':redirect_uri,
                'state':'VA'}
    
    return '%s?%s' % (url,urlencode(params))




def oauth2(request):
    return redirect(get_oauth2_url(request))




def get_logout_url(request):
    url = 'https://account.withings.com/logout'
    oauth2url = get_oauth2_url(request)
    return '%s?%s' % (url,urllib.parse.quote(oauth2url,safe=''))




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
from .utils import timestamp2local




# get the active experiment for a device
def get_active_experiment(hash_deviceid):
    # get all the experiments
    exps = Experiment.objects.all().order_by('-created')
    if exps.count() <=0:
        return None
    
    now_ts = dt.datetime.now().timestamp()

    # look for an active experiment with this deviceid
    for exp in exps:
        is_active = exp.enddate > now_ts and exp.startdate <= now_ts
        if is_active and exp.hash_deviceid == hash_deviceid:
            return exp

    # if nothing hit, then no active experiments
    return None




# render the experiments page
def withings_experiments(request):
    # get all users registered in the local database
    users = UserInfo.objects.all()
    # check token expiration for users to refresh tokens if needed
    for user in users:
        is_token_expired(user.userid)
    
    # get all devices registered in the local database
    devices = Device.objects.all()

    # transform devices into a more django-friendly format and link active experiment
    device_list = []
    for device in devices:
        active_exp = get_active_experiment(device.hash_deviceid)
        record = {
            'id':device.id, 
            'userid':device.userid, 
            'deviceid': device.deviceid,
            'hash_deviceid': device.hash_deviceid, 
            'model': device.model, 
            'mac_address': device.mac_address, 
            'friendlyname': device.friendlyname,
            'first_session_date': str(timestamp2local(device.first_session_date)),
            'last_session_date': str(timestamp2local(device.last_session_date)),
            # exp is the active experiment if one is active (set later), otherwise None
            'exp': None,
            # is_running should be set to True if an active experiment is running
            'is_running': bool(active_exp), 
        }
        if active_exp:
            record['exp'] = {
                'id':active_exp.id, 
                'userid':active_exp.userid, 
                'start_time':str(timestamp2local(active_exp.startdate)), 
                'end_time':str(timestamp2local(active_exp.enddate)), 
                'offset':active_exp.download_offset, 
                'hash_deviceid': active_exp.hash_deviceid, 
            }
        device_list.append(record)

    # get all experiments registered in the local database
    exps = Experiment.objects.all().order_by('-created')
    
    # transform the experiments into a more django-friendly format and link devices
    exp_list = []
    now_ts = dt.datetime.now().timestamp()
    for exp in exps:
        
        # sort the data files associated with this expereiment
        data_files = exp.rawdata_records.order_by('created')

        # determine if this experiment is active
        on_going = False
        if exp.enddate > now_ts and exp.startdate <= now_ts:
            on_going = True
        
        # get the friendlyname the device running this experiment
        exp_devs = devices.filter(hash_deviceid=exp.hash_deviceid)
        devicename = exp.userid
        if exp_devs.count() > 0:
            devicename = exp_devs[0].friendlyname

        record = {
            'id':exp.id, 
            'userid':exp.userid, 
            'start_time':str(timestamp2local(exp.startdate)), 
            'end_time':str(timestamp2local(exp.enddate)), 
            'data_files':data_files, 
            'offset':exp.download_offset, 
            'on_going':on_going, 
            'hash_deviceid': exp.hash_deviceid, 
            'devicename': devicename
        }
        exp_list.append(record)

    # determine the timezone offset for display on the webpage
    timezone_offset = dt.datetime.now(pytz.timezone(settings.TIME_ZONE)).strftime("%Z%z")

    return render(
        request, 
        "withings_experiments.html", 
        {
            'users': users,
            'exp_list': exp_list, 
            'devices': device_list, 
            'context_root': context_root, 
            'timezone': settings.TIME_ZONE, 
            'tz_offset': timezone_offset, 
            'logout_url': get_logout_url(request)
        }
    )
