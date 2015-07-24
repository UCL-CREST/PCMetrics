#!/usr/bin/env python
#
# Generate metrics over reviews from EasyChair.
#
# Jens Krinke <krinke@acm.org>
#

import re
import argparse

parser = argparse.ArgumentParser(description='Generate metrics over reviews from EasyChair.')
parser.add_argument('-a', help='list of names to be anonimised', nargs='+')
parser.add_argument('file', help='review_list.txt file', type=file)
parser.add_argument('-s', help='max. length of short reviews', type=int)
parser.add_argument('-c', help='list of conflicted papers', nargs='+', type=int)
parser.add_argument('-f', help='write metrics to csv file', action='store_true')
parser.add_argument('-g', help='generate a review cluster graph', action='store_true')
args = parser.parse_args()

# list of conflicted aper numbers
if args.c:
    CONFLICTS = args.c
else:
    CONFLICTS = {}

# list of names to be anonimized
ANON = args.a

# max. length of reviews to be considered short
if args.s:
    SHORT_REVIEW = args.s
else:
    SHORT_REVIEW = 1500

# Write graph
GRAPH = args.g

# Write stats
CSV = args.f

# patterns in review_list.txt
score_p = re.compile('([^(:]*)( \(.*\))?: (-?[0-9]) \(([0-9])\)')
review_p = re.compile('\+\+\+\+\+\+\+\+\+\+ REVIEW [0-9]* \((.*)\) \+\+\+\+\+\+\+\+\+')
paper_p = re.compile('\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\* PAPER ([0-9]*) \*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*')

# accumulating variables
reviewers = {}
reviewers_l = {}

# current cluster of reviewers
cluster = []

# counter for anonymization
anon_no = 1

# counter for the length of the current review
review_length = 0

# author of the current review
review_author = ""

# number of the paper
paper_no = ""

f = args.file

# starting state
state = 4

if GRAPH:
    graph_f = open("data.rsf","w")

if CSV:
    stats_f = open("data.csv","w")
    
# parse reviews line by line
for l in f.readlines():
    line = l.strip()
    if state == 0:
        # ignore AUTHORS/TITLE entry
        if line == "================== SUMMARY OF REVIEWS =================":
            # found the start of a review summary block
            # change state
            state = 1
            continue
        # otherwise, ignore the line
    
    if state == 1:
        # Inside a review summary block
        if line.startswith("++++++++++ REVIEW"):
            # found the start of a review, extract reviewer
            m = review_p.match(line)
            review_author = m.group(1)
            # reset the current cluster
            cluster = []
            # change state
            state = 2
            continue
        
        if line.startswith("*********************** PAPER"):
            # found the start of a review block, extract paper number
            m = paper_p.match(line)
            paper_no = m.group(1)
            # reset the current cluster
            cluster = []
            # change state
            state = 0
            continue
        
        if line != "":
            # otherwise, it is a reviewer line with subreviewer, score and confidence
            m = score_p.match(line)
            name =  m.group(1)
            name_sub = m.group(2)
            val = m.group(3)
            conf =  m.group(4)

            # have we seen the reviewer before?
            if not name in reviewers:
                reviewers[name] = []

            # anonymize reviewer if necessary
            if ANON != None and not name in ANON:
                ANON[name] = anon_no
                anon_no += 1

            # anonymize subreviewer if necessary
            if ANON != None and not name_sub in ANON:
                ANON[name_sub] = anon_no
                anon_no += 1

            # store reviewer, subreviewer, score and confidence
            reviewers[name].append((paper_no, name_sub, val, conf))

            # establish a connection between reviewers for clustering
            if GRAPH:
                for c in cluster:
                    if ANON == None:
                        graph_f.write('R "' + name + '" "' + c + '" 1\n')
                    else:
                        graph_f.write('R ' + str(ANON[name]) + ' ' + str(ANON[c]) + ' 1\n')

                cluster.append(name)

    if state == 2:
        # Inside a review header block
        if line.startswith("---- REVIEW ----"):
            # found the start of the actual review
            review_length = 0
            # change state
            state = 3
            continue
        # otherwise, ignore the line
        
    if state == 3:
        # Inside a review
        if line.startswith("---- CONFIDENTIAL REMARKS FOR THE PROGRAM COMMITTEE ----"):
            # found the start of the remarks section
            if not review_author in reviewers_l:
                reviewers_l[review_author] = {}
            # store the length of the review for the reviewer
            reviewers_l[review_author][paper_no] = review_length
            # change state
            state = 4
            continue
        # otherwise, just add the length of the line to the length of the review
        review_length += len(line)

    if state == 4:
        # Either within confidential remarks or outside a review block
        if line.startswith("*********************** PAPER"):
            # found the start of a review block, extract paper number
            m = paper_p.match(line)
            paper_no = m.group(1)
            # reset the current cluster
            cluster = []
            # change state
            state = 0
            continue
        if line.startswith("++++++++++ REVIEW"):
            # found the start of a review, extract reviewer
            m = review_p.match(line)
            review_author = m.group(1)
            # reset the current cluster
            cluster = []
            # change state
            state = 2
            continue
        # otherwise, ignore the line

short_reviews = []

# generate metrics
for r in reviewers:
    # anonimize reviewer if necessary
    if ANON:
        print ANON[r]
    else:
        print r
        
    revs = reviewers[r]
    # generate metrics for current reviewer
    n = 0
    sum_r = 0.0
    sum_ar = 0.0
    sum_c = 0.0
    sum_l = 0.0
    for no,sub,score,conf in revs:
        # ignore conflicted papers
        if no in CONFLICTS:
            continue
        # subreviewer?
        if sub == None:
            print " ", no + ":", "self",
        else:
            # anonymize subreviewer if necessary
            if ANON == None:
                print ' ', no + ":" + sub,
            else:
                print ' ', no + ":" + ANON[sub],
        # length of the review
        l = reviewers_l[r][no]

        print score, conf, l

        n += 1
        sum_r += float(score)
        sum_ar += abs(float(score))
        sum_c += float(conf)
        sum_l += float(l)
        # was this a short review?
        if float(l) < SHORT_REVIEW:
            short_reviews.append((r, no, l))

    # print averages for current reviewer
    print " Average Evaluation:", "%0.2f" % (sum_r / n), "confidence:", "%0.2f" % (sum_c / n)
    print " Average Length:", "%0.0f" % (sum_l / n)
    print " Average Evaluation (ABS):", "%0.2f" % (sum_ar / n)
    print " Sum Evaluation:", "%0.2f" % sum_r, "ABS:", "%0.2f" % sum_ar

    # print averages in csv file
    if CSV:
        stats_f.write(r + ", ")
        stats_f.write("%0.2f, " % (sum_c / n))
        stats_f.write("%0.2f, " % (sum_r / n))
        stats_f.write("%0.2f, " % (sum_ar / n))
        stats_f.write("%0.2f, " % (sum_l / n))
        stats_f.write("\n")

# list all short reviews
print "SHORT REVIEWS (<", SHORT_REVIEW, "characters)"

for r, no, l in short_reviews:
    print r, no, l

# done.
