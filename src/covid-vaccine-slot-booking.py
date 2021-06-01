#!/usr/bin/env python3

#import signal
import copy,threading,subprocess
import traceback
import time,json
from types import SimpleNamespace
import requests, sys, argparse, os, datetime
import jwt,pdb
from utils import generate_token_OTP, generate_token_OTP_manual, check_and_cancel,check_and_book, beep, BENEFICIARIES_URL, WARNING_BEEP_DURATION, \
    display_info_dict, save_user_info, collect_user_details, get_saved_user_info, confirm_and_proceed, get_dose_num, display_table, fetch_beneficiaries


def is_token_valid(token):
    #check for a new token from token.txt
    #pdb.set_trace()
    try:
        file=open('token.txt','r')
        token_info=json.load(file)
        token = token_info['token']
    except Exception as e:
        print(e)
    if token == None:
        return None
    try:
        payload = jwt.JWT().decode(token, do_verify = False)
    except Exception as e:
        print(e)
        return None
    remaining_seconds = payload['exp'] - int(time.time())
    if remaining_seconds <= 1*30: # 30 secs early before expiry for clock issues
        return None
    if remaining_seconds <= 60:
        print("Token is about to expire in next 1 min ...")
    return token
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='Pass token directly')
    parser.add_argument('--cancel', help='To cancel y/n')
    args = parser.parse_args()

    filename = 'vaccine-booking-details-'
    mobile = None

    print('Running Script')
    beep(500, 150)
    proc=subprocess.Popen(["caffeinate", "-d"]) #Prevents display turning off


    try:
        base_request_header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
            'origin': 'https://selfregistration.cowin.gov.in/',
            'referer': 'https://selfregistration.cowin.gov.in/'
        
        }

        token = None
        token=is_token_valid(token) #fetches token from token.txt if valid
        #pdb.set_trace()
        if args.cancel:
            cancel = args.cancel
        else:
            cancel = 'n'
        
        if args.token:
            token = args.token
        print("Sumit  Airtel  Hotspot number : 9028865261")
        print("mintu (Niraj Dete):            9146725202")
        mobile = input("Enter the registered mobile number Default 9028865261: ")
        if mobile == "":mobile='9028865261'
        filename = filename + mobile + ".json"
        while token is None:
                token = generate_token_OTP_manual(mobile, base_request_header)

        request_header = copy.deepcopy(base_request_header)
        request_header["Authorization"] = f"Bearer {token}"

        if os.path.exists(filename):
            print("\n=================================== Note ===================================\n")
            print(f"Info from perhaps a previous run already exists in {filename} in this directory.")
            print(f"IMPORTANT: If this is your first time running this version of the application, DO NOT USE THE FILE!")
            try_file = input("Would you like to see the details and confirm to proceed? (y/n Default y): ")
            try_file = try_file if try_file else 'y'

            if try_file == 'y':
                collected_details = get_saved_user_info(filename,request_header)
                print("\n================================= Info =================================\n")
                display_info_dict(collected_details)

                file_acceptable = input("\nProceed with above info? (y/n Default n): ")
                file_acceptable = file_acceptable if file_acceptable else 'n'
                if file_acceptable != 'y':
                    collected_details = collect_user_details(request_header)
                    save_user_info(filename, collected_details)

            else:
                collected_details = collect_user_details(request_header)
                save_user_info(filename, collected_details)

        else:
            collected_details = collect_user_details(request_header)
            save_user_info(filename, collected_details)
            confirm_and_proceed(collected_details)


        info = SimpleNamespace(**collected_details)

        while True: # infinite-loop
            # create new request_header
            request_header = copy.deepcopy(base_request_header)

            # call function to check and book slots
            try:
                token = is_token_valid(token)

                # token is invalid ? 
                # If yes, generate new one
                if token == None: 
                    print('Token is INVALID.')
                    while token is None:
                        token = generate_token_OTP_manual(mobile, base_request_header)
                request_header["Authorization"] = f"Bearer {token}"

                if cancel == 'y':
                    check_and_cancel(
                    request_header, 
                    )
                    return
                check_and_book(
                    request_header, 
                    info.beneficiary_dtls,
                    info.location_dtls,
                    info.pin_code_location_dtls,
                    info.search_option,
                    min_slots=info.minimum_slots,
                    ref_freq=info.refresh_freq,
                    auto_book=info.auto_book,
                    start_date=info.start_date,
                    vaccine_type=info.vaccine_type,
                    fee_type=info.fee_type,
                    mobile=mobile,
                    captcha_automation=info.captcha_automation,
                    dose_num=get_dose_num(collected_details),
                    do_not_book=info.do_not_book,
                    reschedule=info.reschedule
                            )
            except Exception as e:
                print(traceback.print_exception(type(e),e,e.__traceback__))
                print('Retryin in 5 seconds')
                time.sleep(5)

    except Exception as e:
        print(traceback.print_exception(type(e),e,e.__traceback__))

        proc.kill()
        proc.wait()
        print('Exiting Script')
        


if __name__ == '__main__':
    main()
