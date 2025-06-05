from django.db import models

"""
1. User: code, access_token, user_id
2. Device: hash_deviceid, and other information (provied by withings)

Note: an user can have multiple devices

3. Experiments: start_time, end_time
Note: A devices can have multiple experiments

4. LogFiles: filename (experiment_id, file_id)


"""
# Create your models here.

class UserInfo(models.Model):
    userid = models.CharField(unique=True, max_length=32)

    access_token = models.CharField(max_length=64, null=True)
    refresh_token = models.CharField(max_length=64, null=True)
    scope = models.CharField(max_length=256, null=True)
    expires_in = models.IntegerField(default=10800, null=True)
    csrf_token = models.CharField(max_length=64, null=True)
    token_type = models.CharField(max_length=32, null=True)

    updated = models.DateTimeField(null=True)
    created = models.DateTimeField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['userid', 'updated', 'created'])
        ]

class Device(models.Model):
    deviceid = models.CharField(max_length=64)
    hash_deviceid = models.CharField(max_length=64)
    mac_address = models.CharField(max_length=32)

    type = models.CharField(max_length=32)
    model = models.CharField(max_length=32)
    model_id = models.IntegerField(default=0)
    timezone = models.CharField(max_length=32)
    fw = models.CharField(max_length=32)

    first_session_date = models.IntegerField(default=0)
    last_session_date = models.IntegerField(default=0)

    userid = models.CharField(max_length=32)

    friendlyname=models.CharField(max_length=64)

    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('hash_deviceid', 'userid')]
        indexes = [
            models.Index(fields=['deviceid', 'friendlyname', 'mac_address', 'updated', 'created'])
        ]

class Experiment(models.Model):
    hash_deviceid = models.CharField(max_length=64)
    userid = models.CharField(max_length=32)
    
    startdate = models.IntegerField(default=0)
    enddate = models.IntegerField(default=0)
    
    # This is to indicate whether there are more rawdata to download
    #  0: not started
    # -1: finished
    download_offset = models.IntegerField(default=0)
    
    updated = models.DateTimeField(auto_now=True) # change enddate if stop earlier
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('hash_deviceid', 'startdate')]
        indexes = [
            models.Index(fields=['enddate', 'updated', 'created', 'userid'])
        ]

class RawdataRecord(models.Model):
    exp = models.ForeignKey(Experiment, related_name="rawdata_records", on_delete=models.CASCADE)
    filename = models.CharField(unique=True, max_length=128)
    
    updated = models.DateTimeField(auto_now=True) # change enddate if stop earlier
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['exp_id', 'updated', 'created'])
        ]
