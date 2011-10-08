#!/usr/bin/env python

import sys
import re
import os.path

import urllib2
import json

# API docs:
#   http://code.google.com/p/support/wiki/IssueTrackerAPIPython
import gdata.projecthosting.client
import gdata.projecthosting.data
import gdata.gauth
import gdata.client
import gdata.data
import atom.http_core
import atom.core

# TODO: clean this up
PATCHES_DIRNAME = "."

class PatchBot():
    client = gdata.projecthosting.client.ProjectHostingClient()

    # you can use mewes for complete junk testing
    #PROJECT_NAME = "mewes"
    PROJECT_NAME = "lilypond"

    username = None
    password = None

    def __init__(self):
        # both of these bail if they fail
        self.get_credentials()
        self.login()

    def get_credentials(self):
        # TODO: can we use the coderview cookie for this?
        #filename = os.path.expanduser("~/.codereview_upload_cookies")
        filename = os.path.expanduser("~/.lilypond-project-hosting-login")
        try:
            login_data = open(filename).readlines()
            self.username = login_data[0]
            self.password = login_data[1]
        except:
            print "Could not find stored credentials"
            print "  %(filename)s" % locals()
            print "Please enter loging details manually"
            print
            import getpass
            print "Username (google account name):"
            self.username = raw_input().strip()
            self.password = getpass.getpass()

    def login(self):
        try:
            self.client.client_login(
                self.username, self.password,
                source='lilypond-patch-handler', service='code')
        except:
            print "Incorrect username or password"
            sys.exit(1)


    def update_issue(self, issue_id, description):
        issue = self.client.update_issue(
                self.PROJECT_NAME,
                issue_id,
                self.username,
                comment = description,
                labels = ["Patch-new"])
        return issue

    def get_review_patches(self):
        query = gdata.projecthosting.client.Query(
            canned_query='open',
            label='Patch-Review')
        feed = self.client.get_issues(self.PROJECT_NAME,
            query=query)
        return feed

    def get_new_patches(self):
        query = gdata.projecthosting.client.Query(
            canned_query='open',
            label='Patch-new')
        feed = self.client.get_issues(self.PROJECT_NAME,
            query=query)
        return feed

    # this is stupid, but I couldn't immediately find a better way.
    def id_to_int(self, issue_id):
        stupid_name = ("http://code.google.com/feeds/issues/p/" 
            + self.PROJECT_NAME + "/issues/full/")
        actual_id_string = issue_id.replace(stupid_name,'')
        number = int(actual_id_string)
        return number

    def do_countdown(self):
        issues = self.get_review_patches()
        for i, issue in enumerate(issues.entry):
            print i, '\t', issue.get_id(), '\t', issue.title.text

    def get_urls_from_text(self, text):
        urls = []
        for line in text.splitlines():
            if "http://codereview.appspot.com/" in line:
                # meh, good enough.  Our git-cl makes sure
                # that the patch starts on a newline
                urls.append(line)
        return urls

    def get_rietveld_id_from_issue_tracker(self, issue_id):
        comments_feed = self.client.get_comments(
            self.PROJECT_NAME, issue_id)
        rietveld_id = None
        for comment in comments_feed.entry:
            print comment.content
        # text in the initial issue posting does not count as a
        # "comment".  wtf, google?!  you should know better than
        # this.
        if not rietveld_id:
            query = gdata.projecthosting.client.Query(
                issue_id = issue_id)
            issues = self.client.get_issues("lilypond", query=query)
            issue = issues.entry[0]
            urls = self.get_urls_from_text(issue.content.text)
            if len(urls) != 1:
                print "Problem with urls:"
                print urls
            rietveld_id = urls[0].replace("http://codereview.appspot.com/", "")
        return rietveld_id

    def get_rietveld_patch(self, rietveld_id):
        base_url = "http://codereview.appspot.com"
        data = "/api/" + rietveld_id
        request = urllib2.Request(base_url+data)
        response = urllib2.urlopen(request).read()
        riet_json = json.loads(response)
        patchset = riet_json["patchsets"][-1]

        patch_filename = "issue" + rietveld_id + "_" + str(patchset) + ".diff"
        patch_url = base_url + "/download/" + patch_filename
        request = urllib2.Request(patch_url)
        response = urllib2.urlopen(request).read()
        patch_filename_full = os.path.join(PATCHES_DIRNAME, patch_filename)
        patch_file = open(patch_filename_full, 'w')
        patch_file.write(response)
        patch_file.close()
        return patch_filename_full

    def do_new_check(self):
#        issues = self.get_new_patches()
#        for i, issue in enumerate(issues.entry):
        if 1:
            #issue_id = self.id_to_int(issue.get_id())
#            print i, '\t', issue_id, '\t', issue.title.text
            #issue_id = 1957
            #riet_id = self.get_rietveld_id_from_issue_tracker(issue_id)
            riet_id = str(5242041)
            self.get_rietveld_patch(riet_id)

    def accept_patch(self, issue_id):
        issue = self.client.update_issue(
                self.PROJECT_NAME,
                issue_id,
                self.username,
                comment = "Patchy the autobot says: LGTM",
                labels = ["Patch-Review"])
        return issue


def test_countdown():
    patchy = PatchBot()
    patchy.do_countdown()

def test_new_patches():
    patchy = PatchBot()
    patchy.do_new_check()

def test_accept_patch():
    patchy = PatchBot()
    patchy.accept_patch(1957)

test_accept_patch()
#test_countdown()
#test_new_patches()

