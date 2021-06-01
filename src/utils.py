import signal
import pdb,jwt
import re
import json
import subprocess
import threading
import cv2,pytesseract
import traceback
from hashlib import sha256
from collections import Counter
from inputimeout import inputimeout, TimeoutOccurred
import tabulate, copy, time, datetime, requests, sys, os, random
from captcha import captcha_builder_manual, captcha_builder_auto
import uuid
CANCEL_URL = "https://cdn-api.co-vin.in/api/v2/appointment/cancel"
BOOKING_URL = "https://cdn-api.co-vin.in/api/v2/appointment/schedule"
REBOOKING_URL = "https://cdn-api.co-vin.in/api/v2/appointment/reschedule"
BENEFICIARIES_URL = "https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries"
CALENDAR_URL_DISTRICT = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByDistrict?district_id={0}&date={1}"
CALENDAR_URL_PINCODE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByPin?pincode={0}&date={1}"
CAPTCHA_URL = "https://cdn-api.co-vin.in/api/v2/auth/getRecaptcha"
OTP_PUBLIC_URL = "https://cdn-api.co-vin.in/api/v2/auth/public/generateOTP"
OTP_PRO_URL = "https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP"

WARNING_BEEP_DURATION = (1000, 5000)

origins = ['303,Dhanori Road, Pune, 411015, Maharashtra, India']
#origins = ['B14 Mangal Bhairav, Ghule Patil Nagar, Pandurang Industrial Area, Nanded, Pune, Maharashtra 411041']
#origins = ['ALTTC, Kamla Nehru Nagar, Ghaziabad, Uttar Pradesh']
global_otp = 'not assigned'
kill_otp_from_screenshots =False
global_token = 'not assigned'
flag_update_from_file=True
global_distance_from_home={}
st=time.time()
beneficiaries_choice = ""
kill_otp_from_notifications = False
time_req = []
reccomended_delay=4
additionally_needed_delay=0
try:
    import winsound

except ImportError:
    import os

    if sys.platform == "darwin":

        def beep(freq, duration):
            # brew install SoX --> install SOund eXchange universal sound sample translator on mac
            os.system(
                f"play -n synth {duration / 1000} sin {freq} >/dev/null 2>&1")
    else:

        def beep(freq, duration):
            # apt-get install beep  --> install beep package on linux distros before running
            os.system('beep -f %s -l %s' % (freq, duration))

else:

    def beep(freq, duration):
        winsound.Beep(freq, duration)
def check_req_delay(place="unknown"):
    global time_req
    global reccomended_delay
    global additionally_needed_delay
    temp=time.time()
    if len(time_req) !=0:
        delay = time.time()-time_req[len(time_req)-1]
        delay = round(delay*100)/100
        if delay < reccomended_delay+additionally_needed_delay:
            time.sleep(additionally_needed_delay+reccomended_delay-delay)
        if len(time_req) >=1000:
            time_req.clear()
    time_req.append(time.time())
    #print(f"delay={time.time()-temp:.2f}",end=" ",flush=True)
    #print(str(f"{time.strftime('%H:%M:%S')} req:{place}").ljust(50),end=" ",flush=True)

def global_distance_update_from_file():
    global global_distance_from_home
    
    
    global origins
    
    print(f"NOTE: Calculating distance from {origins}")
    print(
        "==================================================================================="
    )
    try:
        with open(f"{origins[0].replace(' ','_')}.json") as json_file:
            global_distance_from_home = json.load(json_file)
    except FileNotFoundError as e:
        traceback.print_exception(type(e),e,e.__traceback__)
        return
def global_distance_from_home_update_file():
    #pdb.set_trace()
    global global_distance_from_home
    global origins
    with open(f"{origins[0].replace(' ','_')}.json", 'w+') as f:
        # this would place the entire output on one line
        # use json.dump(lista_items, f, indent=4) to "pretty-print" with four spaces per indent
        json.dump(global_distance_from_home, f)
    
def distance_from_home(centers_list):
    global flag_update_from_file
    if flag_update_from_file:
        global_distance_update_from_file()
        flag_update_from_file=False
    ##pdb.set_trace()
    #print(f"distance_from_home{centers_list}")
    global global_distance_from_home
    
    
    global origins
    missing_indices=[]
    for i in range(len(centers_list)):
        #pdb.set_trace()
        if f"{centers_list[i]['center_id']}" in global_distance_from_home:
            centers_list[i].update({"travel":global_distance_from_home[str(centers_list[i]['center_id'])]})
        else:
            missing_indices.append(i)
    #print(missing_indices)
    if len(missing_indices) == 0:
        return
    api_key = 'AIzaSyDI2Xaz2qr80wpzDtyOzYjYA9VdikKmjw0'
    base_url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
    destinations = []
    for j in missing_indices:
        destinations.append(f"{centers_list[j]['address']}, {centers_list[j]['pincode']},{centers_list[j]['district_name']}, ")
    payload = {
        'origins' : '|'.join(origins),
        'destinations' : '|'.join(destinations),
        'mode' : 'driving',
        'key' : api_key
    }
    #print("Calling google distance matrix api")
    #print(payload)
    r = requests.get(base_url, params = payload)
    #print(r.text)
    unknown = {'distance': {'text': 'unknown km', 'value': -1}, 'duration': {'text': 'unknown mins', 'value': -1}}
    googlemap=[]
    if r.status_code != 200:
        print('HTTP status code {} received, program terminated.'.format(r.status_code))
    else:
#        #pdb.set_trace()    
        x = json.loads(r.text)
        if x['status'] == 'OK':
            for row in x['rows']:
                for element in row['elements']:
                    if element['status'] == 'OK':
                        element.pop('status')
                        googlemap.append(element)
                        global_distance_from_home.update({f"{centers_list[i]['center_id']}":copy.deepcopy(element)})
                    else:
                        temp_dest = [f"{centers_list[i]['pincode']}, {centers_list[i]['district_name']}"]
                        temp_payload = {
                            'origins' : '|'.join(origins),
                            'destinations' : '|'.join(temp_dest),
                            'mode' : 'driving',
                            'key' : api_key
                        }
                        #print("Calling google distance matrix api")
                        #print(temp_payload)
                        r1 = requests.get(base_url, params = temp_payload)
                        #print(r1.text)
                        y = json.loads(r.text)
                        if x['status'] == 'OK':
                            if x['rows'][0]['elements'][0]['status'] == 'OK':
                                el = x['rows'][0]['elements'][0]
                                el.pop('status')
                                googlemap.append(el)
                                global_distance_from_home.update({f"{centers_list[i]['center_id']}":copy.deepcopy(el)})
                            else:
                                googlemap.append(copy.deepcopy(unknown))
        else:
            #print(x)
            for i in range (len(missing_indices)):
                googlemap.append(copy.deepcopy(unknown))
    #print(missing_indices)
    
    for i in range(len(missing_indices)):
        if googlemap[i]['distance']['value'] == -1:
            global_distance_from_home.update({f"{centers_list[i]['center_id']}":copy.deepcopy(unknown)})
    for i in range(len(missing_indices)):
        centers_list[missing_indices[i]].update({"travel":   googlemap[i]  })
    global_distance_from_home_update_file()
    
    
    return




#####

def get_all_dist(resp):
    if "centers" in resp:
        if len(resp["centers"]) >= 0:
            for center in resp["centers"]:
                distance_from_home([copy.deepcopy(center)])
        
            

def write_file(cleaned_options_for_display):
    #pdb.set_trace()
    #distance_from_home(cleaned_options_for_display)
    for x in cleaned_options_for_display:
        try:
            filename = f"{x['district_name']}_{x['pincode']}_{x['center_id']}_{x['date']}_{x['age']}.txt"
        except Exception as e:
            print(traceback.print_exception(type(e),e,e.__traceback__))
            filename = "rest_availability.txt"
        file = open(filename,'a')
        x.update({'time':time.strftime('%d-%m-%Y %H:%M:%S')})
        file.write(json.dumps(x))
        file.write('\n')
        file.close()



def record_availability(resp, minimum_slots,dose_num):
    options = []
    if len(resp["centers"]) >= 0:
        for center in resp["centers"]:
            distance_from_home([center])
            for session in center["sessions"]:
                available_capacity = min(session[f'available_capacity_dose{dose_num}'], session['available_capacity'])
                if available_capacity >= minimum_slots:
                    out = {
                        "name": center["name"],
                        "district_name": center["district_name"],
                        "pincode": center["pincode"],
                        "center_id": center["center_id"],
                        "vaccine": session["vaccine"],
                        "fee_type": center["fee_type"],
                        "available": available_capacity,
                        "date": session["date"],
                        "slots": session["slots"],
                        "session_id": session["session_id"],
                        "address": center["address"],
                        "distance": center["travel"],
                        "age":session["min_age_limit"]
                    }
                    options.append(out)
                    print(f"{center['name'].ljust(30)} {session['min_age_limit']}yrs {available_capacity}available {center['travel']['distance']['value']/1000:.1f}km {session['vaccine']}")

                else:
                    pass
    else:
        pass
    write_file(options)
    #if 'centers' in resp:
    #    if len(resp['centers'])>0:
    #        print(str(f" {len(options)} in {len(resp['centers'])} "))
    #    else:print(f"resp['centers']={resp['centers']}")
    #else:print(f"resp={resp}")
    return 
logged = {}
def viable_options(resp, minimum_slots, min_age_booking, fee_type, dose_num):
    global logged
    options = []
    if len(resp["centers"]) >= 0:
        for center in resp["centers"]:
            cent_temp=[copy.deepcopy(center)]
            distance_from_home(cent_temp)
            for session in center["sessions"]:
                #filename = f"{cent_temp[0]['district_name']}_distances_{session['min_age_limit']}.txt"
                #temp_file=open(filename,'a')
                #json.dump(temp_file,center)
                #temp_file.close()
                # Cowin uses slot number for display post login, but checks available_capacity before booking appointment is allowed
                available_capacity = min(session[f'available_capacity_dose{dose_num}'], session['available_capacity'])
                if center["fee_type"] == 'Paid':
                    if 'vaccine_fees' in center:
                        fee = int(center['vaccine_fees'][0]['fee'])
                    else:
                        fee = -1
                else:
                    fee = 0
                if (
                        (available_capacity >= minimum_slots)
                        and (center["fee_type"] in fee_type)
                        and (cent_temp[0]['travel']['distance']['value']<=999999999 )
                        and (fee <= 1000)
                ):
                    print(f"{time.time() }found a session!!!")
                    out = {
                        "name": center["name"],
                        "district": center["district_name"],
                        "pincode": center["pincode"],
                        "center_id": center["center_id"],
                        "vaccine": session["vaccine"],
                        "fee_type": center["fee_type"],
                        "fee": fee,
                        "available": available_capacity,
                        "date": session["date"],
                        "slots": session["slots"],
                        "session_id": session["session_id"],
                        "address": center["address"],
                        "age":session["min_age_limit"],
                        "dist":cent_temp[0]['travel']['distance']['value']
                    }
                    options.append(out)

                else:
                    if session['session_id'] not in logged:
                        print(f"skipping {center['name'].center(35)} {cent_temp[0]['travel']['distance']['text']} {available_capacity} available for {session['date']} fee={fee}")
                        logged.update({session['session_id']:available_capacity})
                    else:
                        if logged[session['session_id']] != available_capacity:
                            print(f"skipping {center['name'].center(35)} {cent_temp[0]['travel']['distance']['text']} {available_capacity} available for {session['date']} fee={fee}")
                            logged.update({session['session_id']:available_capacity})
                            
                    
                    pass
    else:
        pass

    return options


def display_table(dict_list):
    """
    This function
        1. Takes a list of dictionary
        2. Add an Index column, and
        3. Displays the data in tabular format
    """
    if len(dict_list)==0:
        print(f"dict_list empty:{dict_list}")
        return
    header = ["idx"] + list(dict_list[0].keys())
    rows = [[idx + 1] + list(x.values()) for idx, x in enumerate(dict_list)]
    print(tabulate.tabulate(rows, header, tablefmt="grid"))


def display_info_dict(details):
    for key, value in details.items():
        if isinstance(value, list):
            if len(value) > 0 and all(isinstance(item, dict) for item in value):
                print(f"\t{key}:")
                display_table(value)
            else:
                print(f"\t{key}\t: {value}")
        else:
            print(f"\t{key}\t: {value}")


def confirm_and_proceed(collected_details):
    print(
        "\n================================= Confirm Info =================================\n"
    )
    display_info_dict(collected_details)

    confirm = input("\nProceed with above info (y/n Default y) : ")
    confirm = confirm if confirm else "y"
    if confirm != "y":
        print("Details not confirmed. Exiting process.")
        
        sys.exit()


def save_user_info(filename, details):
    print(
        "\n================================= Save Info =================================\n"
    )
    save_info = input(
        "Would you like to save this as a JSON file for easy use next time?: (y/n Default y): "
    )
    save_info = save_info if save_info else "y"
    if save_info == "y":
        with open(filename, "w") as f:
            # JSON pretty save to file
            json.dump(details, f, sort_keys=True, indent=4)
        print(f"Info saved to {filename} in {os.getcwd()}")


def get_saved_user_info(filename,request_header):
    with open(filename, "r") as f:
        data = json.load(f)
    names=[]
    for beneficiary in data['beneficiary_dtls']:
        names.append(beneficiary['name'])
    data['beneficiary_dtls'] = get_beneficiaries(request_header,names)

    # for backward compatible logic
    if data["search_option"] !=3 and "pin_code_location_dtls" not in data:
        data["pin_code_location_dtls"] = []
    return data


def get_dose_num(collected_details):
    # If any person has vaccine detail populated, we imply that they'll be taking second dose
    # Note: Based on the assumption that everyone have the *EXACT SAME* vaccine status
    if any(detail['vaccine']
           for detail in collected_details["beneficiary_dtls"]):
        return 2

    return 1
    
def start_date_search():
        # Get search start date
        start_date = input(
                "\nSearch for next seven day starting from when?\nUse 1 for today, 2 for tomorrow, or provide a date in the format dd-mm-yyyy. Default 2: "
            )
        if not start_date:
            start_date = 2
        elif start_date in ["1", "2"]:
            start_date = int(start_date)
        else:
            try:
                datetime.datetime.strptime(start_date, "%d-%m-%Y")
            except ValueError:
                start_date = 2
                print('Invalid Date! Proceeding with tomorrow.')
        return start_date

def collect_user_details(request_header):
    # Get Beneficiaries
    global beneficiaries_choice
    print("Fetching registered beneficiaries.. ")
    beneficiaries_choice=""
    beneficiary_dtls = get_beneficiaries(request_header)

    if len(beneficiary_dtls) == 0:
        print("There should be at least one beneficiary. Exiting.")
        
        sys.exit(1)
    
    
    # Make sure all beneficiaries have the same type of vaccine
    vaccine_types = [beneficiary["vaccine"] for beneficiary in beneficiary_dtls]
    vaccines = Counter(vaccine_types)

    if len(vaccines.keys()) != 1:
        print(
            f"All beneficiaries in one attempt should have the same vaccine type. Found {len(vaccines.keys())}"
        )
        
        sys.exit(1)

    vaccine_type = vaccine_types[
        0
    ]  # if all([beneficiary['status'] == 'Partially Vaccinated' for beneficiary in beneficiary_dtls]) else None
    if not vaccine_type:
        print(
            "\n================================= Vaccine Info =================================\n"
        )
        vaccine_type = get_vaccine_preference()

    print(
        "\n================================= Location Info =================================\n"
    )
    # get search method to use
    search_option = input(
        """Search by Pincode? Or by State/District Or Smart search State/District for selected Pincodes ? \nEnter 1 for Pincode or 2 for State/District or 3 for State/District filter by Pincodes (Optimized for rate-limit) (Default 2): """
    )

    if not search_option or int(search_option) not in [1, 2, 3]:
        search_option = 2
    else:
        search_option = int(search_option)

    pin_code_location_dtls = []
    if search_option == 3:
        location_dtls = get_districts(request_header)
        pin_code_location_dtls = get_pincodes()
    elif search_option == 2:
        # Collect vaccination center preference
        location_dtls = get_districts(request_header)
    else:
        # Collect vaccination center preference
        location_dtls = get_pincodes()

    print(
        "\n================================= Additional Info =================================\n"
    )

    # Set filter condition
    minimum_slots = input(
        f"Filter out centers with availability less than ? Minimum {len(beneficiary_dtls)} : "
    )
    if minimum_slots:
        minimum_slots = (
            int(minimum_slots)
            if int(minimum_slots) >= len(beneficiary_dtls)
            else len(beneficiary_dtls)
        )
    else:
        minimum_slots = len(beneficiary_dtls)

    # Get refresh frequency
    refresh_freq = input(
        "How often do you want to refresh the calendar (in seconds)? Default 10. Minimum 5. (You might be blocked if the value is too low, in that case please try after a while with a lower frequency) : "
    )

    refresh_freq = int(refresh_freq) if refresh_freq and int(refresh_freq) >= 1 else 15
    
    
    #Checking if partially vaccinated and thereby checking the the due date for dose2
    if all([beneficiary['status'] == 'Partially Vaccinated' for beneficiary in beneficiary_dtls]):
        today=datetime.datetime.today()
        today=today.strftime("%d-%m-%Y")
        due_date = [beneficiary["dose2_due_date"] for beneficiary in beneficiary_dtls]
        dates=Counter(due_date)
        if len(dates.keys()) != 1:
            print(
                f"All beneficiaries in one attempt should have the same due date. Found {len(dates.keys())}"
            )
            
            sys.exit(1)
            
            
        if (datetime.datetime.strptime(due_date[0], "%d-%m-%Y")-datetime.datetime.strptime(str(today), "%d-%m-%Y")).days > 0:
            print("\nHaven't reached the due date for your second dose")
            search_due_date=input(
                "\nDo you want to search for the week starting from your due date(y/n) Default n:"
            )
            if search_due_date=="y":
                
                start_date=due_date[0]
            else:
                
                sys.exit(1)
        else:
            start_date=start_date_search()

    else:
        # Non vaccinated
        start_date=start_date_search()
        
    fee_type = get_fee_type_preference()

    print(
        "\n=========== CAUTION! =========== CAUTION! CAUTION! =============== CAUTION! =======\n"
    )
    print(
        "===== BE CAREFUL WITH THIS OPTION! AUTO-BOOKING WILL BOOK THE FIRST AVAILABLE CENTRE, DATE, AND A RANDOM SLOT! ====="
    )
    auto_book = "yes-please"

    print("\n================================= Captcha Automation =================================\n")

    captcha_automation = input("Do you want to automate captcha autofill? (y/n) Default y: ")
    captcha_automation = "y" if not captcha_automation else captcha_automation
    do_not_book = input("Do you want to just observe and not book?(y/n) Default y: ")
    do_not_book = "y" if not do_not_book else do_not_book
    reschedule = input("Do you want to reschedule? (y/n) Default n: ")
    reschedule = "n" if not reschedule else reschedule
    

    collected_details = {
        "beneficiary_dtls": beneficiary_dtls,
        "location_dtls": location_dtls,
        "pin_code_location_dtls": pin_code_location_dtls,
        "search_option": search_option,
        "minimum_slots": minimum_slots,
        "refresh_freq": refresh_freq,
        "auto_book": auto_book,
        "start_date": start_date,
        "vaccine_type": vaccine_type,
        "fee_type": fee_type,
        'captcha_automation': captcha_automation,
        'do_not_book': do_not_book,
        'reschedule': reschedule,
    }

    return collected_details


def filter_centers_by_age(resp, min_age_booking):
    if min_age_booking >= 45:
        center_age_filter = 45
    else:
        center_age_filter = 18

    if "centers" in resp:
        for center in list(resp["centers"]):
            for session in list(center["sessions"]):
                if session['min_age_limit'] != center_age_filter:
                    center["sessions"].remove(session)
                    if (len(center["sessions"]) == 0):
                        resp["centers"].remove(center)

    return resp
def weekend(start_date):
    return datetime.datetime.fromtimestamp((int(datetime.datetime.strptime(start_date,"%d-%m-%Y").strftime('%s'))+7*24*3600)).strftime('%d-%m-%Y')
def day_words(start_date):
    # x = input_midnight - now
    # input == today =>> 0 to -24hours
    # input->yesterday -->> -24 to -24*2
    # input -> tomorrow ->  24 to 0
    x = int(datetime.datetime.strptime(start_date,"%d-%m-%Y").strftime('%s'))-int(datetime.datetime.today().strftime('%s'))
    if x>-24*60*60 and x<=0:
        return "Today"
    if x>0 and x<=24*60*60:
        return "Tomorrow"
    if x<=-24*60*60 and x>-2*24*60*60:
        return "Yesterday"
    return start_date
def check_calendar_by_district(
        request_header,
        vaccine_type,
        location_dtls,
        start_date,
        minimum_slots,
        min_age_booking,
        fee_type,
        dose_num,
        do_not_book,
        beep_required=True,
        mobile=""
):
    """
    This function
        1. Takes details required to check vaccination calendar
        2. Filters result by minimum number of slots available
        3. Returns False if token is invalid
        4. Returns list of vaccination centers & slots if available
    """
    try:
        print(
            "==================================================================================="
        )
        today = datetime.datetime.today()
        print(f"{today.strftime('%H:%M:%S')}")
        base_url = CALENDAR_URL_DISTRICT
        global additionally_needed_delay
        if vaccine_type:
            base_url += f"&vaccine={vaccine_type}"

        options = []
        len_location_dtls=len(location_dtls)
        max_retries=10
        try:
            loop_counterfile=open('loop_counter.txt',"r")
        except FileNotFoundError as e:
            subprocess.run(f"echo 0 > loop_counter.txt",shell=True)
            loop_counterfile=open('loop_counter.txt',"r") 
        loop_counter = int(loop_counterfile.read())
        loop_counter = (0 + loop_counter) % len_location_dtls
        loop_counterfile.close()
        for i in range(len_location_dtls):
            location = location_dtls[loop_counter]
            #print(f"[{loop_counter}] ",end="",flush=True)
            #if loop_counter !=0:
                #pdb.set_trace()
            retry_counter = 0
            while retry_counter < max_retries:
                retry_counter=retry_counter+1
                check_req_delay(location['district_name'])
                temp=time.time()
                resp = requests.get(
                    base_url.format(location["district_id"], start_date),
                    headers=request_header,
                )
             #   print(f"rr_delay={time.time()-temp:.2f}",end=" ",flush=True)

                if resp.status_code == 401:
                    print("TOKEN INVALID")
                    
                    base_request_header = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
                        'origin': 'https://selfregistration.cowin.gov.in/',
                        'referer': 'https://selfregistration.cowin.gov.in/'
                    
                    }
                    token =None
                    temp=time.time()
                    while token ==None:
                        token = generate_token_OTP_manual(mobile, base_request_header)
              #      print(f"otp_delay={time.time()-temp:.2f}",end=" ",flush=True)
                    request_header = copy.deepcopy(base_request_header)
                    request_header["Authorization"] = f"Bearer {token}"
                elif resp.status_code == 200:
                    resp = resp.json()
                    #get_all_dist(resp)
                    if "centers" in resp:
                        retry_counter = max_retries+1
                        if do_not_book == 'y':
                            temp=time.time()
                            #minimum_slots = 0
                            record_availability(resp, minimum_slots,dose_num)
               #             print(f"r_delay={time.time()-temp:.2f}",end=" ",flush=True)
               #     else:
               #         print(f"not 'centers' in resp. resp={resp}")
                    resp = filter_centers_by_age(resp, min_age_booking)
                    
                    if "centers" in resp:
                        if do_not_book == 'y':
                            #minimum_slots=0
                            pass
                        else:
                            options += viable_options(
                                resp, minimum_slots, min_age_booking, fee_type, dose_num
                            )
              #              print(
              #                  f"From {day_words(start_date)} {len(options)} Sessions available: in {len(resp['centers'])} Centers in {location['district_name']} updated on {today.strftime('%Y-%m-%d %H:%M:%S')} ",end='\r',flush=True
              #              )

                else:
                    if resp.status_code==429:
                        pdb.set_trace()
                        print(str(f"<{resp.status_code}> {resp.reason}"))
                        time.sleep(5)
                        additionally_needed_delay=additionally_needed_delay+0.5
                    else:
                        pdb.set_trace()
                        print(f"<{resp.status_code}> {resp.text}")
            loop_counter = (1 + loop_counter) % len_location_dtls
            loop_counterfile=open('loop_counter.txt',"w")
            loop_counterfile.write(f"{loop_counter}")
            loop_counterfile.close()
            
        #for loop of locations ends here
        if do_not_book == 'y':beep_required=False
        # beep only when needed
        if beep_required:
            for location in location_dtls:
                if location["district_name"] in [option["district"] for option in options]:
                    for _ in range(2):
                        beep(location["alert_freq"], 150)
        return options

    except Exception as e:
        print(traceback.print_exception(type(e),e,e.__traceback__))
        beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])
        


def check_calendar_by_pincode(
        request_header,
        vaccine_type,
        location_dtls,
        start_date,
        minimum_slots,
        min_age_booking,
        fee_type,
        dose_num
):
    """
    This function
        1. Takes details required to check vaccination calendar
        2. Filters result by minimum number of slots available
        3. Returns False if token is invalid
        4. Returns list of vaccination centers & slots if available
    """
    try:
        print(
            "==================================================================================="
        )
        today = datetime.datetime.today()
        base_url = CALENDAR_URL_PINCODE

        if vaccine_type:
            base_url += f"&vaccine={vaccine_type}"

        options = []
        for location in location_dtls:
            check_req_delay()
            resp = requests.get(
                base_url.format(location["pincode"], start_date), headers=request_header
            )

            if resp.status_code == 401:
                print("TOKEN INVALID")
                return False

            elif resp.status_code == 200:
                resp = resp.json()

                resp = filter_centers_by_age(resp, min_age_booking)

                if "centers" in resp:
                    print(
                        f"Centers available in {location['pincode']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                    )
                    options += viable_options(
                        resp, minimum_slots, min_age_booking, fee_type, dose_num
                    )

            else:
                pass

        for location in location_dtls:
            if int(location["pincode"]) in [option["pincode"] for option in options]:
                for _ in range(2):
                    beep(location["alert_freq"], 150)

        return options

    except Exception as e:
        print(str(e))
        beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


def generate_captcha(request_header, captcha_automation):
    print(
        "================================= GETTING CAPTCHA =================================================="
    )
    resp = requests.post(CAPTCHA_URL, headers=request_header)
    print(f'Captcha Response Code: {resp.status_code}')

    if resp.status_code == 200 and captcha_automation == "n":
        return captcha_builder_manual(resp.json())
    elif resp.status_code == 200 and captcha_automation == "y":
        return captcha_builder_auto(resp.json())


def book_appointment(request_header, details, mobile, generate_captcha_pref,reschedule,beneficiary_dtls):
    """
    This function
        1. Takes details in json format
        2. Attempts to book an appointment using the details
        3. Returns True or False depending on Token Validity
           a) 0 - when token is expired
           b) 1 - when token is OK but unable to book due to selected center is completely booked
           c) 2 - when token is OK but unable to book due to any other reason

    """
    try:
        valid_captcha = True
        while valid_captcha:
            print(f"{time.time() }attempting to book the session(getting captcha)!!!")
            captcha = generate_captcha(request_header, generate_captcha_pref)
            # os.system('say "Slot Spotted."')
            details["captcha"] = captcha
   
            print(f"{time.time() }attempting to book the session!!!")
            print(
                "================================= ATTEMPTING BOOKING =================================================="
            )
            if reschedule == 'n':
                resp = requests.post(BOOKING_URL, headers=request_header, json=details)
            else:
                resp = requests.post(REBOOKING_URL, headers=request_header, json=details)
                
            print(f"Booking Response Code: {resp.status_code}")
            print(f"Booking Response : {resp.text}")
            print(f"{time.time() }checking if we booked the session!!!")
            updated_beneficiary_dtls = get_beneficiaries(request_header) 
            if len(beneficiary_dtls)==len(updated_beneficiary_dtls):
                for i in range(len(updated_beneficiary_dtls)):
                    if 'appointments' in beneficiary_dtls[i]:
                        for appointment in updated_beneficiary_dtls[i]['appointments']:
                            if (appointment['session_id'] == details['session_id'] and appointment['slot'] == details['slot']):
                                print(json.dumps(updated_beneficiary_dtls,indent='    '))
                                print(f"{time.time() } booked the session!!!")
                                sys.exit()
            else:
                print(f"len(beneficiary_dtls)={len(beneficiary_dtls)} len(updated_beneficiary_dtls)={len(updated_beneficiary_dtls)}")
            if resp.status_code == 401:
                print("TOKEN INVALID")
                return 0

            elif resp.status_code == 200:
                beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])
                print(
                    "##############    BOOKED!  ############################    BOOKED!  ##############"
                )
                print(
                    "                        Hey, Hey, Hey! It's your lucky day!                       "
                )
                print("\nPress any key thrice to exit program.")
                requests.put("https://kvdb.io/thofdz57BqhTCaiBphDCp/" + str(uuid.uuid4()), data={})
                
                
                
                sys.exit()

            elif resp.status_code == 409:
                print(f"Response: {resp.status_code} : {resp.text}")
                try:
                    data = resp.json()
                    # Response: 409 : {"errorCode":"APPOIN0040","error":"This vaccination center is completely booked for the selected date. Please try another date or vaccination center."}
                    if data.get("errorCode", '') == 'APPOIN0040':
                        return 1
                except Exception as e:
                    print(str(e))
                return 2
            elif resp.status_code == 400:
                print(f"Response: {resp.status_code} : {resp.text}")
                # Response: 400 : {"errorCode":"APPOIN0044", "error":"Please enter valid security code"}
                pass
            elif resp.status_code >= 500:
                print(f"Response: {resp.status_code} : {resp.text}")
                # Server error at the time of high booking
                # Response: 500 : {"message":"Throughput exceeds the current capacity of your table or index.....","code":"ThrottlingException","statusCode":400,"retryable":true}
                pass
            else:
                print(f"Response: {resp.status_code} : {resp.text}")
                return 2

    except Exception as e:
        print(str(e))
        beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])

def check_and_cancel(
        request_header
):
    pdb.set_trace()
    beneficiary_dtls = get_beneficiaries(request_header)
    for beneficiary in beneficiary_dtls:
        if 'appointments' in beneficiary:
            for appointment in beneficiary['appointments']:
                data = {"appointment_id":appointment['appointment_id'],"beneficiariesToCancel":[beneficiary['bref_id']]}
                print(json.dumps(appointment,indent='    '))
                temp=input('ARE YOU SURE YOU WANT TO CANCEL y/n:')
                if temp == 'n':return
                resp = requests.post(url=CANCEL_URL, json=data, headers=request_header)
                if resp.ok:
                    print('Cancelled')
    beneficiary_dtls = get_beneficiaries(request_header)
    for beneficiary in beneficiary_dtls:
        if 'appointments' in beneficiary:
            print(f"{beneficiary['name']} appointments: {beneficiary['appointments']}")
    

def check_and_book(
        request_header, beneficiary_dtls, location_dtls, pin_code_location_dtls, search_option, **kwargs
):
    """
    This function
        1. Checks the vaccination calendar for available slots,
        2. Lists all viable options,
        3. Takes user's choice of vaccination center and slot,
        4. Calls function to book appointment, and
        5. Returns True or False depending on Token Validity
    """
    global reccomended_delay
    slots_available = False
    try:
        min_age_booking = get_min_age(beneficiary_dtls)

        minimum_slots = kwargs["min_slots"]
        refresh_freq = kwargs["ref_freq"]
        auto_book = kwargs["auto_book"]
        start_date = kwargs["start_date"]
        vaccine_type = kwargs["vaccine_type"]
        fee_type = kwargs["fee_type"]
        mobile = kwargs["mobile"]
        captcha_automation = kwargs['captcha_automation']
        do_not_book = kwargs['do_not_book']
        dose_num = kwargs['dose_num']
        reccomended_delay = refresh_freq
        reschedule = kwargs['reschedule']
        if isinstance(start_date, int) and start_date == 2:
            start_date = (
                    datetime.datetime.today() + datetime.timedelta(days=1)
            ).strftime("%d-%m-%Y")
        elif isinstance(start_date, int) and start_date == 1:
            start_date = datetime.datetime.today().strftime("%d-%m-%Y")
        else:
            pass

        if search_option == 3:
            options = check_calendar_by_district(
                request_header,
                vaccine_type,
                location_dtls,
                start_date,
                minimum_slots,
                min_age_booking,
                fee_type,
                dose_num,
                do_not_book,
                beep_required=False
            )

            if not isinstance(options, bool):
                pincode_filtered_options = []
                for option in options: 
                    for location in pin_code_location_dtls:
                        if int(location["pincode"]) == int(option["pincode"]):
                            # ADD this filtered PIN code option
                            pincode_filtered_options.append(option)
                            for _ in range(2):
                                beep(location["alert_freq"], 150)
                options = pincode_filtered_options

        elif search_option == 2:
            options = check_calendar_by_district(
                request_header,
                vaccine_type,
                location_dtls,
                start_date,
                minimum_slots,
                min_age_booking,
                fee_type,
                dose_num,
                do_not_book,
                beep_required=True,
                mobile=mobile
            )
        else:
            options = check_calendar_by_pincode(
                request_header,
                vaccine_type,
                location_dtls,
                start_date,
                minimum_slots,
                min_age_booking,
                fee_type,
                dose_num
            )

        if isinstance(options, bool):
            return False
        options = sorted(
            options,
            key=lambda k: (
                k["district"].lower(),
                k["pincode"],
                k["name"].lower(),
                datetime.datetime.strptime(k["date"], "%d-%m-%Y"),
            ),
        )

        if len(options) > 0:
            if do_not_book == 'n':
                slots_available = True
            else:
                slots_available = False
                time.sleep(refresh_freq)
        else:
            #for i in range(refresh_freq, 0, -1):
            #    msg = f"No viable options. Next update in {i} seconds.."
            #    print(msg, end="\r", flush=True)
            #    sys.stdout.flush()
            #    time.sleep(1)
            time.sleep(refresh_freq)
            slots_available = False

    except TimeoutOccurred as e:
        
        print(traceback.print_exception(type(e),e,e.__traceback__))
        time.sleep(1)
        return True

    else:
        if not slots_available:
            return True
        else:
            # If we reached here then it means there is at-least one center having required doses.

            # sort options based on max available capacity of vaccine doses
            # highest available capacity of vaccine doses first for better chance of booking

            # ==> Caveat: if multiple folks are trying for same region like tier-I or tier-II cities then
            # choosing always first maximum available capacity may be a problem.
            # To solve this problem, we can use bucketization logic on top of available capacity
            #
            # Example:
            # meaning of pair is {center id, available capacity of vaccine doses at the center}
            # options = [{c1, 203}, {c2, 159}, {c3, 180}, {c4, 25}, {c5, 120}]
            #
            # Solution-1) Max available capacity wise ordering of options = [{c1, 203}, {c3, 180}, {c2, 159}, {c5, 120}, {c4, 25}]
            # Solution-2) Max available capacity with simple bucketization wise ordering of options = [{c1, 200}, {c3, 150}, {c2, 150}, {c5, 100}, {c4, 0}] when bucket size = 50
            # Solution-3) Max available capacity with simple bucketization & random seed wise ordering of options = [{c1, 211}, {c2, 180}, {c3, 160}, {c5, 123}, {c4, 15}] when bucket size = 50 + random seed
            #
            # Solution-3) is best as it also maximizing the chance of booking while considering max
            # at the same time it also adds flavour of randomization to handle concurrency.

            BUCKET_SIZE = 50
            options = sorted(
                options,
                key=lambda k: (BUCKET_SIZE*int(k.get('available', 0)/BUCKET_SIZE)) + random.randint(0, BUCKET_SIZE-1),
                reverse=True)
            options = sorted(options,key=lambda k:k['dist'])
            start_epoch = int(time.time())
            #pdb.set_trace()
            options_temp=[]
            print(beneficiary_dtls[0])
            if len(beneficiary_dtls[0]['appointments'])>0:
                for option in options:
                    if option['session_id'] != beneficiary_dtls[0]['appointments'][0]['session_id']:
                        options_temp.append(option)
                    else:
                        print(f"ommiting {option['name'].center(35)} {option['dist']} {option['available']} available for {option['date']} fee={option['fee']}")
                options=options_temp
            # if captcha automation is enabled then have less duration for stale information of centers & slots.
            MAX_ALLOWED_DURATION_OF_STALE_INFORMATION_IN_SECS = 1*60 if captcha_automation == 'n' else 2*60

            # Now try to look into all options unless it is not authentication related issue
            tmp_options = copy.deepcopy(options)
            if len(tmp_options) > 0:
                cleaned_options_for_display = []
                for item in tmp_options:
                    item.pop("session_id", None)
                    item.pop("center_id", None)
                    item.pop("slots", None)
                    item.pop("district", None)
                    item.pop("address", None)
                    cleaned_options_for_display.append(item)
                display_table(cleaned_options_for_display)
            #pdb.set_trace()
            for i in range(0, len(options)):
                option = options[i]
                    
                all_slots_of_a_center = option.get("slots", [])
                all_slots_of_a_center = [all_slots_of_a_center[len(all_slots_of_a_center)-1]]
                #pdb.set_trace()
                if not all_slots_of_a_center:
                    continue
                # For better chances of booking, use random slots of a particular center
                # This will help if too many folks are trying for same region at the same time.
                # Everyone will have better chances of booking otherwise everyone will look for same slot of same center at a time.
                # Randomized slots selection is maximizing chances of booking
                random.shuffle(all_slots_of_a_center) # in-place modification

                for selected_slot in all_slots_of_a_center:
                    # if have spent too much time in loop iteration then means we are looking at stale information about centers & slots.
                    # so we should re-calculate this information while ending this loop more aggressively.
                    current_epoch = int(time.time())
                    if current_epoch - start_epoch >= MAX_ALLOWED_DURATION_OF_STALE_INFORMATION_IN_SECS:
                        print("tried too many centers but still not able to book then look for current status of centers ...")
                        return True

                    try:
                        center_id = option["center_id"]
                        print(f"============> Trying Choice # {i} Center # {center_id}, Slot #{selected_slot}")
                        #pdb.set_trace()
                        dose_num = 2 if [beneficiary["status"] for beneficiary in beneficiary_dtls][0] == "Partially Vaccinated" else 1
                        if reschedule =='n':
                            new_req = {
                                "beneficiaries": [
                                    beneficiary["bref_id"] for beneficiary in beneficiary_dtls
                                ],
                                "dose": dose_num,
                                "center_id": option["center_id"],
                                "session_id": option["session_id"],
                                "slot": selected_slot,
                            }
                        else:
                            new_req = {
                                "appointment_id": beneficiary_dtls[0]['appointments'][0]["appointment_id"],#"3255a383-5ec9-49d6-8972-5c63d1335cfc",#hardcoded found by trying to reschedule from website in web inspecter network "benefeciaries" request
                                "session_id": option["session_id"],
                                "slot": selected_slot,
                            }
                        print(f"Booking with info: {new_req}")
                        booking_status = book_appointment(request_header, new_req, mobile, captcha_automation,reschedule,beneficiary_dtls)
                        # is token error ? If yes then break the loop by returning immediately
                        if booking_status == 0:
                            return False
                        else:
                            # try irrespective of booking status as it will be beneficial choice.
                            # try different center as slots are full for this center
                            # break the slots loop
                            print('Center is fully booked..Trying another...')
                            break
                    except IndexError:
                        print("============> Invalid Option!")
                        
                        pass

            # tried all slots of all centers but still not able to book then look for current status of centers
            return True
def get_vaccine_preference():
    print(
        "It seems you're trying to find a slot for your first dose. Do you have a vaccine preference?"
    )
    preference = input(
        "Enter 0 for No Preference, 1 for COVISHIELD, 2 for COVAXIN, or 3 for SPUTNIK V. Default 0 : "
    )
    preference = int(preference) if preference and int(preference) in [0, 1, 2, 3] else 0

    if preference == 1:
        return "COVISHIELD"
    elif preference == 2:
        return "COVAXIN"
    elif preference == 3:
        return "SPUTNIK V"
    else:
        return None


def get_fee_type_preference():
    print("\nDo you have a fee type preference?")
    preference = input(
        "Enter 0 for No Preference, 1 for Free Only, or 2 for Paid Only. Default 0 : "
    )
    preference = int(preference) if preference and int(preference) in [0, 1, 2] else 0

    if preference == 1:
        return ["Free"]
    elif preference == 2:
        return ["Paid"]
    else:
        return ["Free", "Paid"]


def get_pincodes():
    locations = []
    pincodes = input("Enter comma separated index numbers of pincodes to monitor: ")
    for idx, pincode in enumerate(pincodes.split(",")):
        if not pincode or len(pincode) < 6:
            print(f"Ignoring invalid pincode: {pincode}")
            continue
        pincode = {"pincode": pincode, "alert_freq": 440 + ((2 * idx) * 110)}
        locations.append(pincode)
    return locations


def get_districts(request_header):
    """
    This function
        1. Lists all states, prompts to select one or more,
        2. Lists all districts in those states, prompts to select required ones, and
        3. Returns the list of districts as list(dict)
    """
    check_req_delay("states")
    states = requests.get(
        "https://cdn-api.co-vin.in/api/v2/admin/location/states", headers=request_header
    )

    if states.status_code == 200:
        states = states.json()["states"]

        refined_states = []
        for state in states:
            tmp = {"state": state["state_name"]}
            refined_states.append(tmp)

        display_table(refined_states)
        #state = int(input("\nEnter State index: "))
        #state_id = states[state - 1]["state_id"]
        reqd_states = input(
                "\nEnter comma separated index numbers of districts to monitor (just press enter for all): "
            )
        if reqd_states != '':
            state_idx = [int(idx) - 1 for idx in reqd_states.split(",")]
        else:
            state_idx = []
            for i in range(len(states)):
                state_idx.append(states[i]['state_id'])
        all_districts=[]
        for state_id in state_idx:
            check_req_delay(f"districts for state_id {state_id}")
            districts = requests.get(
                f"https://cdn-api.co-vin.in/api/v2/admin/location/districts/{state_id}",
                headers=request_header,
            )

            if districts.status_code == 200:
                districts = districts.json()["districts"]

                refined_districts = []
                for district in districts:
                    tmp = {"district": district["district_name"]}
                    refined_districts.append(tmp)

                display_table(refined_districts)
                reqd_districts = input(
                    "\nEnter comma separated index numbers of districts to monitor : "
                )
                
                if reqd_districts != '':
                    districts_idx = [int(idx) - 1 for idx in reqd_districts.split(",")]
                else:
                    districts_idx = []
                    for i in range(len(districts)):
                        districts_idx.append(i)
                reqd_districts = [
                    {
                        "district_id": item["district_id"],
                        "district_name": item["district_name"],
                        "alert_freq": 440 + ((2 * idx) * 110),
                    }
                    for idx, item in enumerate(districts)
                    if idx in districts_idx
                ]

                print(f"Selected districts: ")
                display_table(reqd_districts)
                all_districts.extend(reqd_districts)
         

            else:
                print("Unable to fetch districts")
                print(districts.status_code)
                print(districts.text)
                
                sys.exit(1)
        return all_districts
    else:
        print("Unable to fetch states")
        print(states.status_code)
        print(states.text)
        
        sys.exit(1)


def fetch_beneficiaries(request_header):
    check_req_delay('beneficieries')
    return requests.get(BENEFICIARIES_URL, headers=request_header)


    
def vaccine_dose2_duedate(vaccine_type):
    """
    This function
        1.Checks the vaccine type
        2.Returns the appropriate due date for the vaccine type
    """
    covishield_due_date=84
    covaxin_due_date=28
    sputnikV_due_date=21
    
    if vaccine_type=="COVISHIELD":
        return covishield_due_date
    elif vaccine_type=="COVAXIN":
        return covaxin_due_date
    elif vaccine_type=="SPUTNIK V":
        return sputnikV_due_date



def get_beneficiaries(request_header,names=[]):
    """
    This function
        1. Fetches all beneficiaries registered under the mobile number,
        2. Prompts user to select the applicable beneficiaries, and
        3. Returns the list of beneficiaries as list(dict)
    """
    global beneficiaries_choice
    beneficiaries = fetch_beneficiaries(request_header)
    #pdb.set_trace()

    vaccinated=False

    if beneficiaries.status_code == 200:
        beneficiaries = beneficiaries.json()["beneficiaries"]
        

        refined_beneficiaries = []
        for beneficiary in beneficiaries:
            beneficiary["age"] = datetime.datetime.today().year - int(
                beneficiary["birth_year"]
            )
            if beneficiary["vaccination_status"]=="Partially Vaccinated":
                vaccinated=True
                days_remaining=vaccine_dose2_duedate(beneficiary["vaccine"])
                               
                dose1_date=datetime.datetime.strptime(beneficiary["dose1_date"], "%d-%m-%Y")
                beneficiary["dose2_due_date"]=dose1_date+datetime.timedelta(days=days_remaining)
            else:
                vaccinated=False
                #print(beneficiary_2)

            tmp = {
                "bref_id": beneficiary["beneficiary_reference_id"],
                "name": beneficiary["name"],
                "vaccine": beneficiary["vaccine"],
                "age": beneficiary["age"],
                "status": beneficiary["vaccination_status"],
                "dose1_date":beneficiary["dose1_date"],
            }
            if vaccinated:
                tmp["due_date"]=beneficiary["dose2_due_date"]
            refined_beneficiaries.append(tmp)
        
        if names:
            for i in range(len(refined_beneficiaries)):
                if refined_beneficiaries[i]['name'] in names:
                    if beneficiaries_choice == "":
                        beneficiaries_choice=f"{i+1}"
                    else:
                        beneficiaries_choice=f"{beneficiaries_choice},{i+1}"
        if beneficiaries_choice == "":
            display_table(refined_beneficiaries)
            #print(refined_beneficiaries)
            print(
                """
            ################# IMPORTANT NOTES #################
            # 1. While selecting beneficiaries, make sure that selected beneficiaries are all taking the same dose: either first OR second.
            #    Please do no try to club together booking for first dose for one beneficiary and second dose for another beneficiary.
            #
            # 2. While selecting beneficiaries, also make sure that beneficiaries selected for second dose are all taking the same vaccine: COVISHIELD OR COVAXIN.
            #    Please do no try to club together booking for beneficiary taking COVISHIELD with beneficiary taking COVAXIN.
            #
            # 3. If you're selecting multiple beneficiaries, make sure all are of the same age group (45+ or 18+) as defined by the govt.
            #    Please do not try to club together booking for younger and older beneficiaries.
            ###################################################
            """
            )
            reqd_beneficiaries = input(
                "Enter comma separated index numbers of beneficiaries to book for : "
            )
            beneficiaries_choice= reqd_beneficiaries 
        else:
            reqd_beneficiaries = beneficiaries_choice
        beneficiary_idx = [int(idx) - 1 for idx in reqd_beneficiaries.split(",")]
        reqd_beneficiaries = [
            {
                "bref_id": item["beneficiary_reference_id"],
                "name": item["name"],
                "vaccine": item["vaccine"],
                "age": item["age"],
                "status": item["vaccination_status"],
                "dose1_date":item["dose1_date"],
                "appointments":item["appointments"]
            }
                                
            for idx, item in enumerate(beneficiaries)
            if idx in beneficiary_idx
        ]

        for beneficiary in reqd_beneficiaries:
                if beneficiary["status"]=="Partially Vaccinated":
                    days_remaining=vaccine_dose2_duedate(beneficiary["vaccine"])
                        
                    dose1_date=datetime.datetime.strptime(beneficiary["dose1_date"], "%d-%m-%Y")
                    dose2DueDate=dose1_date+datetime.timedelta(days=days_remaining)
                    beneficiary["dose2_due_date"]=dose2DueDate.strftime("%d-%m-%Y")

        if beneficiaries_choice == "":
            print(f"Selected beneficiaries: ")
            display_table(reqd_beneficiaries)
        return reqd_beneficiaries

    else:
        print("Unable to fetch beneficiaries")
        print(beneficiaries.status_code)
        print(beneficiaries.text)
        
        return []


def get_min_age(beneficiary_dtls):
    """
    This function returns a min age argument, based on age of all beneficiaries
    :param beneficiary_dtls:
    :return: min_age:int
    """
    age_list = [item["age"] for item in beneficiary_dtls]
    min_age = min(age_list)
    return min_age


def clear_bucket_and_send_OTP(storage_url, mobile, request_header):
    print("clearing OTP bucket: " + storage_url)
    response = requests.put(storage_url, data={})
    data = {
        "mobile": mobile,
        "secret": "U2FsdGVkX1+z/4Nr9nta+2DrVJSv7KS6VoQUSQ1ZXYDx/CJUkWxFYG6P3iM/VW+6jLQ9RDQVzp/RcZ8kbT41xw==",
    }
    print(f"Requesting OTP with mobile number {mobile}..")
    check_req_delay('generateMobileOTP')
    txnId = requests.post(
        url="https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP",
        json=data,
        headers=request_header,
    )

    if txnId.status_code == 200:
        txnId = txnId.json()["txnId"]
    else:
        print("Unable to Create OTP")
        print(txnId.text)
        time.sleep(5)  # Saftey net againt rate limit
        txnId = None

    return txnId


def generate_token_OTP(mobile, request_header):
    """
    This function generate OTP and returns a new token or None when not able to get token
    """
    storage_url = "https://kvdb.io/ASth4wnvVDPkg2bdjsiqMN/" + mobile

    txnId = clear_bucket_and_send_OTP(storage_url, mobile, request_header)

    if txnId is None:
        return txnId

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

    print("Parsed OTP:" + OTP)

    data = {"otp": sha256(str(OTP.strip()).encode("utf-8")).hexdigest(), "txnId": txnId}
    print(f"Validating OTP..")

    check_req_delay("validateMobileOtp")
    token = requests.post(
        url="https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp",
        json=data,
        headers=request_header,
    )
    if token.status_code == 200:
        token = token.json()["token"]
    else:
        print("Unable to Validate OTP")
        print(token.text)
        return None

    print(f"Token Generated: {jwt.JWT().decode(token,do_verify=False,do_time_check=False)}")
    return token

def input_with_timeout(prompt,timeout):
    #not sure how to implement timeout
    global global_otp
    global st
    print("you may enter otp in otp.txt")
    subprocess.run("open -t otp.txt",shell=True)
    subprocess.run("osascript -e 'quit app \"Preview\"'",shell=True)
    while time.time()-st<timeout:
        try:
            mod_time=subprocess.check_output(["date", "-r", "otp.txt", "+%s"])
            if int(mod_time)>st-1:
                otpfile=open('otp.txt','r')
                answer=otpfile.readline().strip()
                otpfile.close()
                subprocess.run("osascript -e 'quit app \"TextEdit\"'",shell=True)
                subprocess.run("open -a Terminal",shell=True)
                print(f"Received otp {answer} in otp.txt")
                
                kill_otp_from_notifications = True
                return answer
            #else:
            #    print(f"mod_time={int(mod_time)}")
            #    print(f"st-1={st-1}")
        except Exception as e:
            print(e)
        time.sleep(1)
        print(f"{time.strftime('%M:%S',time.gmtime(round(timeout-time.time()+st)))}",end='\r',flush=True)
    print("Timeout")
    kill_otp_from_notifications = True
    return 'not assigned'

def otp_from_notifications():
    global st
    global global_token
    global kill_otp_from_notifications
    notifications_watcher = subprocess.Popen("osascript read_cowin_otp.applescript",shell=True)
    while notifications_watcher.returncode == None:
        try:
            token_file=open('token.txt','r')
            token_time = json.load(token_file)
            if time.time()-jwt.JWT().decode(token_time['token'],do_verify=False)['iat'] < 3*60:
                global_token = token_time['token']
                file=open('otp.txt','w')
                file.write('token')
                print(f"{time.time()} wrote token in otp.txt")
                break
        except Exception as e:
            print(e)
        if kill_otp_from_notifications:
            break
        if time.time()-st>=3*60:
            break
        mod_time=subprocess.check_output(["date", "-r", "otp.txt", "+%s"])
        if int(mod_time)>st-1:
            break
        time.sleep(1)
        notifications_watcher.poll()

    notifications_watcher.kill()
    notifications_watcher.wait()
    return
        

def otp_from_screenshots():
    return
    global global_token
    global kill_otp_from_screenshots
    global st
    answer = 'unknown'
    #print(f"{time.strftime('%H:%M:%S')} START")
    flag_popup=True
    while time.time()-st<3*60:
        try:
            mod_time=subprocess.check_output(["date", "-r", "otp.txt", "+%s"])
            if int(mod_time)>st-1:
                file=open('otp.txt','r')
                print(f"otp_screenshots shutting down bcz modtime={mod_time}")
                return
        except Exception as e:
            print(e)
        try:
            token_file=open('token.txt','r')
            token_time = json.load(token_file)
            if time.time()-jwt.JWT().decode(token_time['token'],do_verify=False)['iat'] < 3*60:
                global_token = token_time['token']
                file=open('otp.txt','w')
                file.write('token')
                print(f"{time.time()} wrote token in otp.txt")
                return
        except Exception as e:
            print(e)
        subprocess.run("screencapture otp.jpg",shell=True)
        img=cv2.imread('./otp.jpg')
        #83 1120 14 290
        roi = img[83:83+14,1120:1120+290]
        #740 480 75 475
        roi1 = img[740:740+75,480:480+475]
        #pdb.set_trace()
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
    otpfile=open('otp.txt','w')
    otpfile.write(answer)
    otpfile.close()
    return answer


def generate_token_OTP_manual(mobile, request_header):
    """
    This function generate OTP and returns a new token
    """
    global global_otp
    global global_token
    global st
    if not mobile:
        print("Mobile number cannot be empty")
        os.system('pause')
        sys.exit()
    
    valid_token = False
    while not valid_token:
        try:
            data = {"mobile": mobile,
                    "secret": "U2FsdGVkX1+z/4Nr9nta+2DrVJSv7KS6VoQUSQ1ZXYDx/CJUkWxFYG6P3iM/VW+6jLQ9RDQVzp/RcZ8kbT41xw=="
                    }
            global_otp='not assigned' 
            kill_otp_from_screenshots=False
            kill_otp_from_notifications=False
            st=time.time()
            t1 = threading.Thread(target=otp_from_screenshots)
            t1.start()
            t2 = threading.Thread(target=otp_from_notifications)
            t2.start()
            check_req_delay("requested OTP")
            txnId = requests.post(url=OTP_PRO_URL, json=data, headers=request_header)

            if txnId.status_code == 200:
                print(f"Successfully requested OTP for mobile number {mobile} at {datetime.datetime.today()}..")
                txnId = txnId.json()['txnId']
                OTP =input_with_timeout('Enter otp',180)
                print(f"{datetime.datetime.today().strftime('%H:%M:%S.%f')} Waiting for t2 &t1.join()")
                t1.join()
                t2.join()
                print(f"{datetime.datetime.today().strftime('%H:%M:%S.%f')} yayy! t1 &t2 .join()")

                #OTP = input("Enter OTP (If this takes more than 2 minutes, press Enter to retry): ")
                if OTP == 'token':
                    token = global_token
                    if t1.is_alive():
                        print("t1 should not be alive, global_token is assigned")
                        t1.join()
                    return token
                if OTP == 'not assigned':
                    print("DID not receive OTP")
                elif OTP:
                    data = {"otp": sha256(str(OTP).encode('utf-8')).hexdigest(), "txnId": txnId}
                    print(f"Validating OTP..")
                    check_req_delay("Validating OTP")
                    token = requests.post(url='https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp', json=data,
                                          headers=request_header)
                    if token.status_code == 200:
                        file=open('token.txt','w')
                        json.dump(token.json(),file)
                        file.close()
                        token = token.json()['token']
                        print(f"Token Generated: {jwt.JWT().decode(token,do_verify=False,do_time_check=False)}")
                        valid_token = True
                        return token

                    else:
                        print('Unable to Validate OTP')
                        print(f"Response: {token.text}")


            else:
                kill_otp_from_screenshots=True
                kill_otp_from_notifications = True
                t1.join()
                t2.join()
                print('Unable to Generate OTP')
                print(txnId.status_code, txnId.text)


        except Exception as e:
            kill_otp_from_screenshots = True
            kill_otp_from_notifications = True
            t1.join()
            t2.join()
            time.sleep(5)
            
            print(traceback.print_exception(type(e),e,e.__traceback__))
