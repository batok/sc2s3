#!/bin/env python
# -*- coding: iso-8859-1 -*-

#Copyright 2009  Domingo Aguilera

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import configobj
conf = configobj.ConfigObj("sc2s3.ini")
acc = conf.get("preferred_account","")

preferred_account = acc
arn_sns = conf.get(acc).get("arn_sns")
bitly_apikey = conf.get(acc).get("bitly_apikey")
bitly_login = conf.get(acc).get("bitly_login")
gravatar = conf.get(acc).get("gravatar")
message = conf.get(acc).get("message")
preferred_bucket = conf.get(acc).get("preferred_bucket")
twitter_message = conf.get(acc).get("twitter_message")
twitter_password = conf.get(acc).get("twitter_password")
twitter_user = conf.get(acc).get("twitter_user")
accounts = { acc: [conf.get(acc).get("aws_access_key_id"),conf.get(acc).get("aws_secret_access_key")]}
