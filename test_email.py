import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

port = 587
smtp_server = 'smtp.gmail.com'
sender_email = 'cameraproject99@gmail.com'
password = 'nopi pjsn dnug zbeq'
receiver_email = 'stamenkovichnik@gmail.com'


message = MIMEMultipart('alternative')
message['Subject'] = 'Email test'
message['From'] = sender_email
message['To'] = receiver_email

text = """\
Hi,Your account has been successfully aproved by admin
"""
html = """\
<html>
  <body>
    <p>
    Hi,Your account has been successfully aproved by admin
    </p>
  </body>
</html>
"""
part1 = MIMEText(text, 'plain')
part2 = MIMEText(html, 'html')

message.attach(part1)
message.attach(part2)

context = ssl.create_default_context()

with smtplib.SMTP(smtp_server, port) as server:
    #server.ehlo()
    server.starttls(context=context)
    #server.ehlo()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, message.as_string())

