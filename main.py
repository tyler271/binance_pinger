from announcement_parser import AnnoucementParser
import http.client as httplib
import os
import re
import requests
import sched
import smtplib
import sys
import time

LAST_COIN = None

def run_process(parser, conn):
    global LAST_COIN
    print(f"GET Binance at {int(round(time.time() * 1000, 0))}ms")
    binance_success_flag = False
    i = 0
    while (not binance_success_flag) and (i < 3):
        try:
            announcement_url = "/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=1"
            conn.request("GET", url)
            response = conn.getresponse()
            announcement = json.loads(response.read().decode("utf-8"))["data"]["articles"][0]["title"]
            binance_success_flag = True
        except Exception as e:
            print(f"Exception \"{str(e)}\" encountered at {int(round(time.time() * 1000, 0))}ms")
            time.sleep(1)
            i += 1

    if not binance_success_flag:
        raise Exception("binance GET request failed 3 times!")

    coin = parser.find_coin(announcement)
    if coin is not None and coin != LAST_COIN:
        coin_bytes = coin.encode("utf-8")
        nexus_url = os.environ["NEXUS_SERVER_URL"] + "/report_coin"
        post_time = time.time()
        response = requests.post(nexus_url, data=coin_bytes)
        print(f"made POST request to nexus server at epoch {int(round(post_time * 1000, 0))}ms")
        LAST_COIN = coin
        if response.status_code != 200:
            raise Exception("exception trying to POST to nexus server")
        else:
            print(f"successfully posted coin={coin} to nexus server")
    print(f"announcement={announcement}")

def extract_epoch(param):
    m = re.search("^epoch=([0-9]*)$", param)
    if m is not None:
        return int(m.group(1))
    else:
        return None

def extract_sleep_sec(param):
    m = re.search("^sleep_sec=([0-9]*)$", param)
    if m is not None:
        return int(m.group(1))
    else:
        return None

def extract_conn_close_interval(param):
    m = re.search("^conn_close_interval=([0-9]*)$", param)
    if m is not None:
        return int(m.group(1))
    else:
        return None

def extract_node_index(param):
    m = re.search("^node_index=([0-9]*)$", param)
    if m is not None:
        return int(m.group(1))
    else:
        return None

def extract_node_count(param):
    m = re.search("^node_count=([0-9]*)$", param)
    if m is not None:
        return int(m.group(1))
    else:
        return None

def send_email(sender_gmail_addr, sender_gmail_pass, receiver, subject, body):
    receiver_list = [receiver]
    message = f"""From: From MyCryptoBot <{sender_gmail_addr}>
To: To Person <{receiver_list[0]}>
Subject: {subject}

{body}.
"""
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_gmail_addr, sender_gmail_pass)
        server.sendmail(sender_gmail_addr, receiver, message)
    except smtplib.SMTPException as e:
        print(f"Error: unable to send email: {str(e)}")
        raise

def send_email_with_retries(sender_gmail_addr, sender_gmail_pass, receiver, subject, body, retries=3):
    success_flag = False
    i = 0
    while not success_flag and i < retries:
        try:
            send_email(sender_gmail_addr, sender_gmail_pass, receiver, subject, body)
            success_flag = True
        except:
            time.sleep(30)
            i += 1
    if not success_flag:
        raise

if __name__ == "__main__":
    print("@main")
    input_epoch = None
    sleep_seconds = 10
    conn_close_interval = 30
    node_index = None
    node_count = None
    if len(sys.argv) > 1:
        for param in sys.argv[1:]:
            if extract_epoch(param) is not None:
                input_epoch = extract_epoch(param)
            elif extract_sleep_sec(param) is not None:
                sleep_seconds = extract_sleep_sec(param)
            elif extract_conn_close_interval(param) is not None:
                conn_close_interval = extract_conn_close_interval(param)
            elif extract_node_index(param) is not None:
                node_index = extract_node_index(param)
            elif extract_node_count(param) is not None:
                node_count = extract_node_count(param)

    if (input_epoch is None) or (node_index is None) or (node_count is None):
        raise Exception("missing required argument!")

    parser = AnnoucementParser()

    try:
        # Main loop
        start_epoch = input_epoch + 1500 + node_index * (sleep_seconds / node_count)
        print(f"start_epoch={start_epoch}, sleep_seconds={sleep_seconds}")
        scheduler = sched.scheduler(time.time, time.sleep);
        if start_epoch < time.time() + 2:
            raise Exception("given start time has already elapsed!")
        priority = 1
        i = 0

        sender_gmail_addr = os.environ["NOTIFICATION_EMAIL_SENDER_ADDR"]
        sender_gmail_pass = os.environ["NOTIFICATION_EMAIL_SENDER_PASS"]
        receiver = os.environ["NOTIFICATION_EMAIL_RECEIVER_ADDR"]
        node_id = os.environ["NODE_ID"]
        subject = f"PROCESS START SUCCESSFULL ON NODE {node_id}"
        body = "hello world"
        send_email_with_retries(sender_gmail_addr, sender_gmail_pass, receiver, subject, body)
        conn = None
        while True:
            if i % conn_close_interval == 0:
                if conn is not None:
                    conn.close()
                host = "www.binance.com"
                conn = httplib.HTTPSConnection(host)
                conn.connect()

            loop_exec_time_epoch = start_epoch + i * sleep_seconds
            scheduler.enterabs(loop_exec_time_epoch, priority, run_process, argument=(parser, conn))
            scheduler.run()
            i += 1

    except Exception as e:
        print(str(e))
        # Send email notification
        print("send email alerting the error")
        sender_gmail_addr = os.environ["NOTIFICATION_EMAIL_SENDER_ADDR"]
        sender_gmail_pass = os.environ["NOTIFICATION_EMAIL_SENDER_PASS"]
        receiver = os.environ["NOTIFICATION_EMAIL_RECEIVER_ADDR"]
        node_id = os.environ["NODE_ID"]
        subject = f"ERROR OCCURRED WHILE RUNNING PROCESS ON NODE {node_id}"
        body = "hello world"
        send_email_with_retries(sender_gmail_addr, sender_gmail_pass, receiver, subject, body)
