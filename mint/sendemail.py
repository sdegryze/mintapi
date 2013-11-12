__author__ = 'sdegryze'

#! /usr/bin/python

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def sendemail(msg_content, from_addr, to_addr, username, password):

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Your portfolio allocation"
    msg['From'] = from_addr
    msg['To'] = to_addr

    # Create the body of the message (a plain-text and an HTML version).
    # text is your plain-text email
    # html is your html version of the email
    # if the reciever is able to view html emails then only the html
    # email will be displayed
    #text = "Hi!\nHow are you?\n"
    html = """\n
    <html>
      <head></head>
      <body>
        Hi!<br>
           How are you?<br>

      </body>
    </html>
    """

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(msg_content, 'plain')
    #part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    msg.attach(part1)
    #msg.attach(part2)

    # The actual mail send
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username,password)
    server.sendmail(from_addr, to_addr, msg.as_string())
    server.quit()