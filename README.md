# Withings Experiment Server

The Withings Experiment Server is an instance of Django that is designed to manage activity tracking experiments for Withings devices. The Withings Scanwatch model was used in developing and testing the web app server. The device is equipped with a triaxial accelerometer with a dynamic range of ±4g and a possible sampling rate of up to 100 Hz (with 25 Hz as a default rate). 

Collecting and extracting epoch level data with the Withings trackers require advanced setup and API integration. This process involves the use of the tracker (Withings watch), Withings phone app, and Server. This document details how the server application enables starting, tracking, and fetching activity tracking experiments from the Withings servers.

## Getting started with Withings
Collecting epoch data with Withings trackers requires activating the research mode on the device (watch) via the rawdata API from Withings. The following steps explain the activation process.   

### Create an account with access to the Advanced Research API
[Create an account with Withings](https://developer.withings.com/dashboard). The account is free, and all accounts have access to the developer dashboard. 

Enter your email address, and a verification code will be sent to it.

### Create an application in the Developer Dashboard
From the developer dashbaord, click "Create an Application." Choose the Public API, and agree to the terms of use.

Choose an application name, and provide a valid callback URL. This URL must be publically accessible from Withings Servers. A callback endpoint is provided with this server, but feel free to use a different application for this if so desired.

Take note of the Client ID and Client Secret. You will need to supply these to the server application.

### Request rawdata API access
Create a ticket on the [Withings Developer Dashboard](https://developer.withings.com/dashboard/) to request access to the rawdata API. Access is granted to an application, so include the Client ID along with the ticket. 

## Server application

Check out this repository, and use the install.sh script to install `withings_server` in your environment:

```bash
./install.sh
```

Alternatively, a Dockerfile is included in this repository if you wish to create a container.

### Configuration
The following settings can be used to configure Withings Experiment Server.
The server will look for configuration options in the following order:
 * Environment variables
 * Files named as the variable and contents of the value in the directory containing `manage.py`
 * Files named as the variable and contents of the value at /run/secrets

For example, the variable `WITHINGS_HOSTNAME` could be set with an environment 
variable or with the contents of a file at `/run/secrets/WITHINGS_HOSTNAME`.

| Parameter | Default | Description |
| --- | --- | --- |
| `WITHINGS_DEBUG` | False | Displays webpages with debug info when an exception occurs |
| `WITHINGS_HOSTNAME` | localhost | The hostname of the server, used for `ALLOWED_HOSTS` and CSRF settings |
| `WITHINGS_CONTEXT_ROOT` | withings | Context that this will be deployed, what comes after `WITHINGS_HOSTNAME` in the URL |
| `WITHINGS_REDIRECT_URI` | https://`WITHINGS_HOSTNAME`/`WITHINGS_CONTEXT_ROOT`/callback/ | Callback URI registered with Withings that will complete oauth2 transactions |
| `WITHINGS_CLIENT_ID` | none | Client ID supplied by Withings for this application
| `WITHINGS_CLIENT_SECRET` | none | Client Secret supplied by Withings for this application
| `WITHINGS_DJANGO_SECURE_KEY` | django-insecure-please-consider-supplying-a-secure-key-23^%36n4Gdf | Django Secret Key used for cryptographic signing ([docs](https://docs.djangoproject.com/en/5.2/topics/signing/))
| `WITHINGS_TIME_ZONE` | System time (`tzlocal.get_localzone_name`) | Timezone that experiment times should be displayed in

### Systemd service
If it is desirable to run this as a service, create a definition file at /etc/systemd/system. 

For example, this service definition file (`/etc/systemd/system/withings.service`) exists for an installation at `/opt/withings_server`. The `WITHINGS_HOSTNAME` and `WITHINGS_DEBUG` variables are defined in the service definition below. The Client ID and Client Secret are read from file at /run/secret since they are not defined as environment variables. The other settings use default values.
```
[Unit]
Description="CSSM PAHP Withings Service"
After=network.target

[Service]
Type=exec
User=django
Environment=WITHINGS_HOSTNAME=foo.cssm.iastate.edu
Environment=WITHINGS_DEBUG=True
WorkingDirectory=/opt/withings_server
ExecStart=/opt/withings_server/.venv/bin/gunicorn withings_server.wsgi:application --name withings --workers 3 --user django --group django --bind=127.0.0.1:8000 --log-level=debug --log-file=-

[Install]
WantedBy=multi-user.target
```

### Usage
If running as a service
```
sudo systemctl start withings
```

If executing from the command line
```
.venv/bin/gunicorn withings_server.wsgi:application --name withings --workers 3 --user django --group django --bind=127.0.0.1:8000 --log-level=debug --log-file=-
```

Access the server at https://`WITHINGS_HOSTNAME`/`WITHINGS_CONTEXT_ROOT`. For the example service definition above, this would be https://foo.cssm.iastate.edu/withings since the default `WITHINGS_CONTEXT_ROOT` of "withings" was used.

Setting up an experiment on the server

You will be prompted to authenticate Withings through the phone app (if you are not currently in a session) and then you will be prompted to authorize the application to manage your devices. Grant access, and you should be redirected to the experiments page.

On the experiment page, start an experiment by setting the date and click “Run Experiment.” The experiment will begin and run until the specified time range. Note that extended experiments (>24 hours at a default rate of 25 Hz) are likely to drain the battery and therefore, not finish. Thus, it is recommended to keep the experiment at a maximum of 24 hours.  

When an experiment is completed, click on Fetch Data. Once fetched, a link to the file will be provided for download. The waiting time before data is made available for download is currently unknown but estimated to be between (immediately- 24 hours). 

Download and save the data locally 

Start a new experiment. 


