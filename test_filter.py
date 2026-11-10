import sys, os, imaplib, email as emaillib, re, datetime as dt
from collections import Counter

PHOENIX_METRO = {
    "phoenix","tempe","scottsdale","chandler","mesa","gilbert","glendale","peoria",
    "surprise","avondale","goodyear","buckeye","ahwatukee","maricopa","queen creek",
    "apache junction","fountain hills","cave creek","paradise valley","sun city",
    "tolleson","el mirage","youngtown","litchfield park","az","arizona",
}
def classify_workplace(location):
    loc = location.lower()
    has_remote  = "remote" in loc or "anywhere" in loc
    has_phoenix = any(c in loc for c in PHOENIX_METRO)
    if has_remote and not has_phoenix:
        other_st = re.search(r"\b([A-Z]{2})\b", location)
        if other_st and other_st.group(1) not in ("AZ", "US"):
            return "other"
        return "remote"
    if has_phoenix and has_remote:  return "phoenix_remote"
    if has_phoenix:                 return "onsite_hybrid"
    if has_remote:                  return "remote"
    return "other"

env = open("/proc/1/environ","rb").read().split(b"\x00")
gmail_user = next((e.decode().split("=",1)[1] for e in env if e.startswith(b"GMAIL_ADDRESS=")), "")
gmail_pass = next((e.decode().split("=",1)[1] for e in env if e.startswith(b"GMAIL_APP_PASSWORD=")), "")

LEAD_SENDERS = [
    "jobalerts-noreply@linkedin.com","jobalert@linkedin.com","jobs-listings@linkedin.com",
    "donotreply@jobalert.indeed.com","alert@indeed.com","alerts@dice.com",
    "noreply@clearancejobs.com","jobs@clearancejobs.com","noreply@builtin.com",
    "alerts@ziprecruiter.com","jobalert@glassdoor.com",
]
mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(gmail_user, gmail_pass)
since = (dt.datetime.now() - dt.timedelta(days=7)).strftime("%d-%b-%Y")
locs = []
for sender in LEAD_SENDERS:
    for folder in ['"[Gmail]/All Mail"', "INBOX"]:
        try:
            mail.select(folder, readonly=True)
            _, data = mail.search(None, '(FROM "' + sender + '" SINCE ' + since + ')')
            ids = data[0].split() if data[0] else []
            for mid in ids[-10:]:
                try:
                    _, md = mail.fetch(mid, "(RFC822)")
                    msg = emaillib.message_from_bytes(md[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8","ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8","ignore")
                    for block in re.split(r"-{10,}", body):
                        lines = [l.strip() for l in block.splitlines() if l.strip()]
                        for i, line in enumerate(lines):
                            if re.search(r"View job:", line, re.IGNORECASE) and i >= 2:
                                loc = lines[i-1] if i >= 1 else ""
                                locs.append((loc, classify_workplace(loc), sender.split("@")[-1]))
                except Exception as ex:
                    print("err:", ex)
            if ids:
                break
        except Exception as ex:
            pass
mail.logout()
print("LOCATION SAMPLES (first 30):")
for loc, cls, src in locs[:30]:
    print("  [{:15}] {!r}  ({})".format(cls, loc, src))
print()
print("CLASS COUNTS:", Counter(c for _,c,_ in locs))
