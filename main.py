from announcement_parser import AnnoucementParser
from binance_webscraper import BinanceWebscraper
import sched
import smtplib
import sys
import time

LAST_COIN = None

def run_process(parser, webscraper):
    url = os.environ["NEXUS_SERVER_URL"] + "/report_coin"
    announcement = webscraper.get_latest_annoucement()
    coin = parser.find_coin(announcement)
    if coin is not None and coin != LAST_COIN:
        coin_bytes = coin.encode("utf-8")
        response = requests.post(url, data=coin_bytes)
        global LAST_COIN
        LAST_COIN = coin
        if response.status_code != 200:
            raise Exception("exception trying to POST to nexus server")

def extract_exec_time_epoch(param):
    m = re.search("^start=([0-9]*)$", param)
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
    exec_time_epoch = None
    sleep_seconds = 60
    if len(sys.argv) > 1:
        for param in sys.argv[1:]:
            if extract_exec_time_epoch(param) is not None:
                exec_time_epoch = extract_exec_time_epoch(param)
            elif extract_sleep_sec(param) is not None:
                sleep_seconds = extract_sleep_sec(param)
    parser = AnnoucementParser()
    webscraper = BinanceWebscraper()

    try:
        # Main loop
        scheduler = sched.scheduler(time.time, time.sleep);
        if exec_time_epoch is None:
            exec_time_epoch = time.time() + 2
        elif exec_time_epoch < time.time() + 2:
            raise Exception("given start time has already elapsed!")
        priority = 1
        i = 0
        while True:
            loop_exec_time_epoch = exec_time_epoch + i * sleep_seconds
            scheduler.enterabs(loop_exec_time_epoch, priority, run_process, argument=(parser, webscraper))
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
