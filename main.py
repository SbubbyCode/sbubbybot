# Sheen Patel
# u/SbubbyBot for the the mods of r/Sbubby

import threading  # to be able to run in threads
import praw  # all the reddit i/o
import os  # to get enviroment variables containing secrets
import psycopg2  # used for postgresql database stuff
from datetime import datetime  # need to get current time for multiple things
import time  # for time.sleep
from dotenv import load_dotenv  # need this to import env. vars
from sys import exit  # to exit gracefully from Ctrl+c
from signal import signal, SIGINT  # to exit gracefully from C
import re  # regex for the modmail
from digiformatter import styles #VT-100 formatting for console text
import logging  #logging
from digiformatter import logger as digilogger  #better logging
import importlib.resources as pkg_resources #  read files in reliably
import sbubbybot.data  # load resources

# Set up logging
logging.basicConfig(level=logging.INFO)
dfhandler = digilogger.DigiFormatterHandler()

logger = logging.getLogger("sbubbybot")
logger.handlers = []
logger.propagate = False
logger.addHandler(dfhandler)

styles.create("angry", fg="dark_orange", attr="bold", prefix="ANGY", showtime=True, showprefix=True)

# load env variables (only for locally testing, heroku takes care of it othewise)
load_dotenv()

# Setting this var to true will allow the bot to actually comment on the post and not dry-run.
PRODUCTION = False

# create the reddit instance for the bot to use
reddit = praw.Reddit(
    user_agent='SbubbyBot v. 1.0 by u/CrazedPatel',
    client_id=os.environ['client_id'],
    client_secret=os.environ['client_secret'],
    username=os.environ['reddit_username'],
    password=os.environ['reddit_password'])

# mark the subreddit
sbubby = reddit.subreddit('sbubby')

# MAGIC_EYE_BOT's profile
# magicEye = reddit.redditor('MAGIC_EYE_BOT')

database = ""
# connect to the postgresql database
try:
    database = psycopg2.connect(user="postgres", password=os.environ['database_password'],
                                database=os.environ["database_name"], host=os.environ["DATABASE_URL"], port="5432")
except Exception as err:
    logger.error(err)
    logger.warn("Error connecting normal way, try other way")
    database = psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')

cur = database.cursor()

# Load the sunday message from file. (this only happens once so it's minimal impact on performance.)
sunday_message = pkg_resources.read_text(sbubbybot.data, "sunday_message.txt")


def main():
    #    if True:  # use this if for testing small things.
    #        for i in reddit.subreddit('finnkennedy').modmail.conversations(limit=20):
    #            print(i.subject)
    #            print("\t", i.obj_ids)
    #        return
    logger.info("creating threads")
    oneMinTimerThread = threading.Thread(target=oneMinTimerThreadFunc)
    repostAndFlairThread = threading.Thread(target=repostAndFlairThreadFunc)
    logger.info("starting threads")
    oneMinTimerThread.start()
    repostAndFlairThread.start()
    logger.info("threads started")


def repostAndFlairThreadFunc():
    logger.info("repost and flair thread started")
    for submission in sbubby.stream.submissions():
        # skip post if author is moderator
        moderators = sbubby.moderator()
        if submission.author in moderators:
            continue

        # only do the stuff if the post hasn't been clicked
        if submission.clicked is False:
            doFlair(submission)
            commonRepost(submission)
            # need to commit after each time because of other thread and bc forever for loop
            database.commit()


def oneMinTimerThreadFunc():  # not exactly one minute
    logger.info("one Min Timer thread started")
    while True:
        # check for any flair stuff that needs to be checked up on
        checkFlairDB()
        howMuchKarmaModmail()

        # attempt to do sunday sbubday, making sure there is no duplicates is handled in the function
        attemptSundaySbubday()

        time.sleep(60)  # 1 min rest

        
def sundaySbubby():
    logger.info("It is sunday. Sunday Sbubby started...")
    # Get and remove the flair templates:
    for flairTemp in sbubby.flair.templates:
        print(flairTemp)
        if flairTemp == "Eaten Fresh" or flairTemp == "IRL" or flairTemp == "Logoswap":
            # found flair to remove -- now removing it!
            if PRODUCTION:  # only actually remove if production is on
                sbubby.flair.templates.update(flairTemp["id"], mod_only=True)
    # get the automod post.
    # sort subreddit by new for author:AutoModerator
    link = None
    message = None
    linkMessage = "Please see the comments for the post to request new Sbubbies."
    for submission in sbubby.search("author:AutoModerator", sort="new", time_filter="day"):
        # only want to use the first one because it is the most recent
        link = submission
        linkMessage = f"[Go to the latest request thread here to request a sbubby]({link.url})"
        break
    if link is None:
        # we weren't able to find a link, so fail angrily!!!
        styles.print("Could not find the Automoderator link! will use placeholder!", style = "angry")
        message = sunday_message.format(linkMessage)
    # with the message, now post it and sticky it. Unsticky the automod post
    if PRODUCTION:
        if link is not None:
            if link.stickied:
                link.mod.sticky(state=False)
        submission = sbubby.submit("Sunday Sbubday is today!", selftext=message)
        submission.mod.distinguish(how='yes', sticky=True)  # stickies to the top


def unSundaySbubby():
    # add flairs eaten Fresh, Logoswap, IRL,
    # unsticky announcement post,
    # resticky requests post
    if PRODUCTION:
        for flairTemp in sbubby.flair.templates:
            if flairTemp == "Eaten Fresh" or flairTemp == "IRL" or flairTemp == "Logoswap":
                # found flair to remove -- now removing it!
                if PRODUCTION:  # only actually remove if production is on
                    sbubby.flair.templates.update(flairTemp["id"], mod_only=False)

        # unsticky my post by searching through all the stickied posts to find the one authored by me
        for i in range(1, 5):
            try:
                stickied = sbubby.sticky(number=i)
                if stickied.author == reddit.user.me():
                    stickied.mod.sticky(state=False)
            except Exception as err:
                logger.error(err)
                break
        # sticky most recent automod post.
        for submission in sbubby.search("author:AutoModerator", sort="new", time_filter="week"):
            submission.mod.sticky(state=True, bottom=False)
            break

def attemptSundaySbubday():
    logger.info("<Sunday Sbubday> Attempting to do a sunday sbubday activity!")
    today = datetime.today().weekday()

    # check whether there is a post. stickyNum = 0 means no post
    stickyNum = 0
    for i in range(1, 3):
        try:
            post = sbubby.sticky()
            if "Sunday Sbubday" in post.title:
                stickyNum = i
                break  # there is a post, no need to do anything.
        except Exception as err:
            logger.error(err)
            logger.warn("no sticky at index ", i)
            break  # no more sticky posts, need to add post

    logger.info(today)
    if today == 6:
        # sunday, check if already post, if not, post
        logger.info("it is sunday")
        if stickyNum == 0:
            sundaySbubby()
    elif today == 0:
        # monday
        logger.info("it is monday")
        if stickyNum != 0:
            unSundaySbubby()


def checkFlairDB():
    logger.info("<Database> checking flair db")
    cur.execute("select * from flairs;")
    rows = cur.fetchall()

    # row[0] = submission id, row[1] = time post created, row[2] = comment telling to flair id.
    for row in rows:
        epochTime = row[1].timestamp()
        now = datetime.now().timestamp()
        submission = reddit.submission(row[0])  # lazy instance of the thing
        # check if the post should be removed, otherwise, do nothing
        link_flair_text = 0
        try:
            link_flair_text = submission.link_flair_text
        except Exception as err:
            logger.error(err)
            logger.warn("error could not get")

        if now - epochTime > 590 and link_flair_text is None:
            # remove the post.
            logger.info("<Database> Post ", submission.id, " is past the time and has no flair.")
            logger.info("<Database> Time's up! Remove post.")

            # remove from database
            cur.execute(f"DELETE from flairs where submission_id='{row[0]}';")

            # do the comment thing
            try:
                if PRODUCTION:
                    comment_id = row[2]
                    if comment_id is None:
                        # need to find the real one
                        submission.comments.replace_more(limit=None)
                        for comment in submission.comments:
                            if comment.author == reddit.user.me():
                                comment_id = comment.id
                        logger.info("no comment found by me")
                        continue  # continues with the next submission in db
                    reddit.comment(comment_id).delete()

                    if sbubby.user_is_moderator:
                        # remove post
                        submission.mod.remove(mod_note="Removed for lack of flair by sbubbybot")
                        submission.mod.send_removal_message("Hi! Your post was removed because it had no flair after 10 minutes of you being notified to flair your post. This messsage was sent automatically, if you think it's an error, send a modmail")
                        submission.unsave()
            except Exception as err:
                logger.error(err)
                logger.warn("<Database> Could not do: post could have been deleted?? postid=", row[0])

        elif submission.link_flair_text is None:
            # there is a flair.
            logger.info(f"<Database> {submission.id} already has flair, removing from db.")
            cur.execute(f"DELETE from flairs where submission_id='{row[0]}';")
            if PRODUCTION:
                # remove the comment as the flair is set
                comment_id = row[2]
                if comment_id is None:
                    # need to find the real one
                    submission.comments.replace_more(limit=None)
                    for comment in submission.comments:
                        if comment.author == reddit.user.me():
                            comment_id = comment.id
                    logger.info("no comment found by me")
                    continue  # continues with the next submission in db
                reddit.comment(comment_id).delete()

    database.commit()  # once all the querys set, then execute all at once.


def doFlair(submission):
    # check to see if flair first
    logger.info("<Flair> Checking ", submission.id)
    if submission.link_flair_text is None and submission.saved is False:
        # check to see if post already been messaged
        hasBeenMessaged = False
        for comment in submission.comments:
            if comment.author == reddit.user.me():  # if i have a top level comment then don't message
                hasBeenMessaged = True
        if not hasBeenMessaged:
            submission.save()
            logger.info(f"<Flair> message {submission.name} post to remind to flair!")
            logger.info("<Flair>   created on: ", submission.created_utc)
            comment_id = None  # only used if PRODUCTION is true, will still insert into db as None
            if PRODUCTION:
                # make a comment on this post.
                comment = submission.reply("""# It seems you didn't flair your post!
                Please flair your post now or it might get taken down!
                This comment was made by a bot (contact me @ u/CrazedPatel)""")
                if comment is not None:
                    comment_id = comment.id
            cur.execute(f"INSERT INTO FLAIRS (submission_id, time_created, comment_id) VALUES ('{submission.id}', to_timestamp({submission.created_utc}), '{comment_id}') ON CONFLICT (submission_id) DO NOTHING")
        else:
            logger.info("<Flair> No need for flair message -- one already exists?")


def howMuchKarmaModmail():
    logger.info("<Karma> Anti-\"how much karma\" bot started...")
    for conversation in sbubby.modmail.conversations(limit=20):
        # for each mail, check for specific keywords: "How much Karma" "Karma requirement" "Karma minimum"
        for message in conversation.messages:
            messageBody = message.body_markdown
            # need to check if is a message or not, only do things in messages.
            regex = r"karma.*minimum|minimum.*karma|How much.*karma|karma.*requirement|required.*karma"
            regexmatch = re.search(regex, messageBody, flags=re.I)
            if regexmatch:
                # there is at least one occurence of this, so do thing
                if PRODUCTION:
                    conversation.reply("Thank you for your message, but it seems that this message is asking about the Karma requirement to post on r/sbubby. The Karma minimum is to help prevent spam and is secret. If your message is not about the Karma reqirement, please send a new message without the word Karma in it. Thanks :) This message was sent by the u/sbubbybot and is not perfect. We are working on improving it!")


def commonRepost(submission):
    logger.info("<Repost> Common reposts bot started...")
    # TODO: Check each item in the imgur album -- if any is over the threshold:
    #       make a comment with the similarity amount, and then give link that it is similar to.
    #       mark post as spam(, and if user replies, then send modmail?)


def sigintHandler(signal, frame):
    print(f"\u001b[3D Received (most likely) Ctrl+c, exiting.")
    database.close()
    exit(0)


if __name__ == "__main__":
    signal(SIGINT, sigintHandler)
    main()
