from rest_framework import serializers

from withings.models import UserInfo, Device, Experiment, RawdataRecord

class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        #fields = ['id', 'userid', 'access_token', 'refresh_token', 'scope', 'expires_in', 'csrf_token', 'token_type', 'updated', 'created']
        fields = ['id', 'userid', 'updated', 'created']


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'deviceid', 'hash_deviceid', 'mac_address', 'type', 'model', 'model_id', 'timezone', 'fw', 'userid', 'first_session_date', 'last_session_date', 'updated', 'created', 'friendlyname']

class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'hash_deviceid', 'userid', 'startdate', 'enddate', 'download_offset', 'updated', 'created']
        

class RawdataRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawdataRecord
        fields = '__all__'