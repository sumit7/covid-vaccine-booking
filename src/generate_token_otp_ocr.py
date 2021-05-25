#!/usr/bin/env python3
import traceback
import cv2
import signal
import jwt
import re
import threading
import subprocess
import pytesseract
import copy
import pdb
from hashlib import sha256
from types import SimpleNamespace
import requests, sys, argparse, os, datetime, time,json
global_otp = '000000'
kill_otp_from_screenshots =False
delay_req = 4
requests_timelog = []
global_token = ''
def requests_in_last5mins(flag=False):
    if len(requests_timelog)>1:
        delay = time.time()-requests_timelog[len(requests_timelog)-1]['time']
        if delay<delay_req:
            #print(f"sleeping for{delay_req-delay}seconds")
            time.sleep(delay_req-delay)
    count=0
    i=len(requests_timelog)-1
    temp_arr1=[0,0,0,0,0,0,0,0,0,0,0,0]
    while i>=0:
         if time.time()-requests_timelog[i]['time'] > 5*60:
             break
         temp_arr1[requests_timelog[i]['place']]=temp_arr1[requests_timelog[i]['place']]+1
         i=i-1
    count = len(requests_timelog) -i-1
    print(f"{count:03d} {temp_arr1} requests_in_last5mins {datetime.datetime.today().strftime('%H:%M:%S')}")
    if count%10==1:
        print(f"{count:03d} {temp_arr1} requests_in_last5mins {datetime.datetime.today().strftime('%H:%M:%S')}")
    if flag:
        print(f"{count:03d} {temp_arr1} requests_in_last5mins{datetime.datetime.today().strftime('%H:%M:%S')}")
    if count >99:
        print(f"{count:03d} requests_in_last5mins{datetime.datetime.today().strftime('%H:%M:%S')} Target:{time.ctime(5*60+requests_timelog[len(requests_timelog)-100])}")
        temp=5*60+requests_timelog[len(requests_timelog)-100]['time']-time.time()
        if temp>0:
            temp_arr=[0,0,0,0,0,0,0,0,0,0,0,0]
            j=len(requests_timelog)-1
            while j>len(requests_timelog)-1-100:
                temp_arr[requests_timelog[j]['place']]=temp_arr[requests_timelog[j]['place']]+1
            print(f"requests:{temp_arr}")
            print(f"sleeping for {temp}seconds")
            sleep(temp)
        count = requests_in_last5mins()
    return count

def input_with_timeout(prompt,timeout):
    #not sure how to implement timeout
    global global_otp
    global_otp = input(prompt)
    print(f"YOU TYPED:{global_otp}")
    return
def otp_from_screenshots():
    global global_otp
    global global_token
    global kill_otp_from_screenshots
    st=time.time()
    answer = 'unknown'
    #print(f"{time.strftime('%H:%M:%S')} START")
    flag_popup=True
    while time.time()-st<3*60:
        try:
            token_file=open('tokenfile.txt','r')
            token_time = json.load(token_file)
            if time.time()-float(token_time['time']) < 3*60:
                global_token = token_time['token']
                global_otp='token'
                return
        except Exception as e:
            pass
        subprocess.run("screencapture otp.jpg",shell=True)
        img=cv2.imread('./otp.jpg')
        #83 1120 14 290
        roi = img[83:83+14,1120:1120+290]
        #740 480 75 475
        roi1 = img[740:740+75,480:480+475]
        if flag_popup:
            cv2.imwrite('out.jpg',roi)
            subprocess.run(f"open out.jpg",shell=True)
            flag_popup=False
        text = pytesseract.image_to_string(roi)
        text1 = pytesseract.image_to_string(roi1)
        #print(f"{time.strftime('%H:%M:%S')} OCR for otp:\"{text.strip()}\" or \"{text1.strip()}\"",end='\r')
        if 'cowin' in text1.lower():
            x=re.findall('[^0-9][0-9] min',text1)
            if len(x) == 1:
                if int(x[0][1]) <3:
                    text=text1
                    roi=copy.deepcopy(roi1)
            else:
                if 'now' in text1.lower():
                    text = text1
                    roi=copy.deepcopy(roi1)
        if 'cowin' in text.lower():
            answers = re.findall('[^0-9][0-9][0-9][0-9][0-9][0-9][0-9][^0-9]',text)
            if len(answers)==1:
                answer = answers[0][1:7]
                cv2.imwrite(f"{answer}.jpg",roi)
                break
            cv2.imwrite(f"{time.strftime('%H-%M-%S-%f')}.jpg",roi)
        time.sleep(1)
        if kill_otp_from_screenshots:
            return
    #print(f"{time.strftime('%H:%M:%S')} OCR for otp:\"{text.strip()}\"")
    global_otp=answer
    return answer

def generate_token_OTP(mobile, request_header, device_os):
    global requests_timelog
    global global_otp
    global kill_otp_from_screenshots
    global global_token
    """
    This function generate OTP and returns a new token or None when not able to get token
    """
    if device_os == 'android':
        storage_url = "https://kvdb.io/3YgXf9PHYHbX6NsF7zP6Us/" + mobile
        print("clearing OTP bucket: " + storage_url)
        response = requests.put(storage_url, data={})
    data = {
        "mobile": mobile,
        "secret": "U2FsdGVkX1+z/4Nr9nta+2DrVJSv7KS6VoQUSQ1ZXYDx/CJUkWxFYG6P3iM/VW+6jLQ9RDQVzp/RcZ8kbT41xw==",
    }
    print(f"Requesting OTP with mobile number {mobile}..")
    kill_otp_from_screenshots = False
    global_otp='not assigned'
    otp_requested =time.time()
    t1 = threading.Thread(target=otp_from_screenshots)
    t1.start()
    t2 = threading.Thread(target=input_with_timeout,args=('Enter otp',180))
    t2.start()
    try:
        txnId = requests.post(
            url="https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP",
            json=data,
            headers=request_header,
        )
        requests_in_last5mins()
        requests_timelog.append({'time':time.time(),'place':8})
    except Exception as e:
        traceback.print_exception(type(e),e,e.__traceback__)
        kill_otp_from_screenshots=True
        t1.join()
        return None
    
    if txnId.status_code == 200:
        txnId = txnId.json()["txnId"]
        print("Your Transaction ID for OTP is ", txnId)
        while global_otp == 'not assigned':
            time.sleep(1)
        kill_otp_with_screenshots = True
        OTP=global_otp
        if global_otp == 'token':
            return global_token
    else:
        kill_otp_from_screenshots=True
        t1.join()
        print("Unable to Create OTP")
        print(txnId.text)
        time.sleep(5)  # Saftey net againt rate limit
        return None

    if device_os == "ios":
        pass
        #global_otp="000000"
        ##OTP = input_with_timeout("Enter the OTP:",180)
        #OTP = otp_from_screenshots()
        #global_otp=OTP
    else:
        time.sleep(10)
        t_end = time.time() + 60 * 3  # try to read OTP for atmost 3 minutes
        while time.time() < t_end:
            response = requests.get(storage_url)
            if response.status_code == 200:
                print("OTP SMS is:" + response.text)
                print("OTP SMS len is:" + str(len(response.text)))

                OTP = response.text
                OTP = OTP.replace("Your OTP to register/access CoWIN is ", "")
                OTP = OTP.replace(". It will be valid for 3 minutes. - CoWIN", "")
                if not OTP:
                    time.sleep(5)
                    continue
                break
            else:
                # Hope it won't 500 a little later
                print("error fetching OTP API:" + response.text)
                time.sleep(5)

    if not OTP:
        return None
    flag_t = True
    while flag_t:
        if 180-time.time()+otp_requested<=0:
            return None
        print("Parsed OTP:" + OTP)
    
        data = {"otp": sha256(str(OTP).encode("utf-8")).hexdigest(), "txnId": txnId}
        print(f"Validating OTP..")
        flag_e=True
        while flag_e:
            try:
                print(time.strftime('%H:%M:%S'))
                token = requests.post(
                    url="https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp",
                    json=data,
                    headers=request_header,
                )
                print(time.strftime('%H:%M:%S'))
                print(token.json())
                if token.status_code != 504:
                    flag_e=False
            except Exception as e:
                traceback.print_exception(type(e),e,e.__traceback__)
                flag_e=True
                time.sleep(1)
        if token.status_code == 200:
            token = token.json()["token"]
            token_file=open('tokenfile.txt','w')
            temp_token_time={'token':token,'time':time.time()}
            json.dump(temp_token_time,token_file)
            token_file.close()
            flag_t = False
        else:
            print("Unable to Validate OTP")
            print(token.text)
            if not t2.is_alive():
                global_otp = 'not assigned'
                t2 = threading.Thread(target=input_with_timeout,args=("Enter the OTP",180-time.time()+otp_requested))
                t2.start()
                while global_otp == 'not assigned':
                    time.sleep(1)
                    if 180-time.time()+otp_requested<=0:
                        return None
                if global_otp =='token':
                    return global_token
                OTP=global_otp
            if t2.is_alive():
                global_otp='not assigned'
                while global_otp == 'not assigned':
                    time.sleep(1)
                    if 180-time.time()+otp_requested<=0:
                        return None
                if global_otp =='token':
                    return global_token
                OTP=global_otp
            

    print(f"Token Generated in file tokenfile.txt\nDecoded token: {jwt.JWT().decode(token,do_verify=False)}")
    print(f"{time.ctime(jwt.JWT().decode(token,do_verify=False)['iat']).split()[3]} Start")
    print(f"{time.ctime(jwt.JWT().decode(token,do_verify=False)['exp']).split()[3]} Expiry")
    return token

def main():
    time_start=time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='Pass token directly')
    parser.add_argument('--device_os', help='Pass device os directly')
    args = parser.parse_args()

    mobile = None

    print('Running Script')

#try:
    base_request_header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        'origin':'https://selfregistration.cowin.gov.in',
        'referer':'https://selfregistration.cowin.gov.in/',
        'sec-fetch-dest':'empty',
        'sec-fetch-mode':'cors',
        'sec-fetch-site':'cross-site',
    }

    token = None
    if args.device_os:
        device_os = args.device_os
    if args.token:
        token = args.token
    print("Ashoknagar Aknit Badkul      : 8884351234")
    print("my hotspot number(for dhayri): 9028865261")
    mobile = input("Enter the registered mobile number: ")
    t = time.time()
    while True:
        while token is None:
            token = generate_token_OTP(mobile, base_request_header, device_os)
        expiry = jwt.JWT().decode(token,do_verify=False)['exp']
        token =None
        while time.time()< expiry-4*60:
            time.sleep(1)
            print(f"{time.strftime('%H:%M:%S')}",end='\r')
    return


if __name__ == '__main__':
    main()

