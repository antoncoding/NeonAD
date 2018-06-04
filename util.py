from boa.interop.Neo.Storage import GetContext, Put, Delete, Get
from boa.builtins import concat

def get_content_key(board_id):
    return concat(board_id, ".content")

def get_owner_key(board_id):
    return concat(board_id, ".owner")

def get_endtime_key(board_id):
    return concat(board_id, ".endtime")

def get_highest_bidder_key(board_id):
    return concat(board_id, ".highest_bidder")

def get_highest_bid_key(board_id):
    return concat(board_id, ".highest_bid")

def get_period_key(board_id):
    return concat(board_id, ".period")

def get_next_content_key(board_id):
    return concat(board_id, ".content.next")

def get_owner_key(board_id):
    return concat(board_id, ".owner")

def get_ad_admin_key(board_id):
    return concat(board_id, ".admin")

def get_domain_key(board_id):
    return concat(board_id, ".domain")
