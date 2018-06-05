from boa.interop.Neo.Runtime import CheckWitness, Log, GetTime, GetTrigger
from boa.interop.Neo.Storage import GetContext, Put, Delete, Get
from boa.interop.Neo.Blockchain import GetHeader, GetHeight
from boa.interop.Neo.Header import GetTimestamp
from boa.interop.Neo.TriggerType import Application, Verification
from boa.builtins import concat
# Key and other function Definition
from util import *
# ICO Template
from nad.txio import get_asset_attachments
from nad.token import *
from nad.crowdsale import *
from nad.nep5 import *

ctx = GetContext()
NEP5_METHODS = ['name', 'symbol', 'decimals', 'totalSupply', 'balanceOf', 'transfer', 'transferFrom', 'approve', 'allowance']


def Main(operation, args):
    """
    Main definition for the smart contracts

    :param operation: the operation to be performed
    :param args: list of arguments.
        args[0] is always sender script hash
    """
    # Triggers, From ICO template
    trigger = GetTrigger()
    if trigger == Verification():
        print('Trigger == Verification')
        if CheckWitness(CONTRACT_OWNER):
            return True

        attachments = get_asset_attachments()
        return can_exchange(ctx, attachments, True)

    # Main Application Operation
    elif trigger == Application():
        for op in NEP5_METHODS:
            if operation == op:
                return handle_nep51(ctx, operation, args)

        # Functions that can be called by anyone
        if operation == "getEndTime":
            return get_endtime(ctx, args)


        # ICO crowdsale function
        elif operation == 'circulation':
            return get_circulation(ctx)

        elif operation == 'mintTokens':
            return perform_exchange(ctx)

        elif operation == 'crowdsale_register':
            return kyc_register(ctx, args)

        elif operation == 'crowdsale_status':
            return kyc_status(ctx, args)

        elif operation == 'crowdsale_available':
            return crowdsale_available_amount(ctx)

        elif operation == 'get_attachments':
            return get_asset_attachments()

        # # Main Operations on SC
        # # Functions that Require Authorization
        user_hash = args[0]
        authorized = CheckWitness(user_hash)
        if not authorized:
            return False
        Log("Authorized")

        if operation == "createBoard":
            return create_board(ctx, args)

        elif operation == "bidForBoard":
            return bid_for_ad(ctx, args)

        elif operation == "editContent":
            return edit_content(ctx, args)

        # Functions Only Available from Contract Owner
        elif operation == "setDefaultContent":
            return set_default_content(ctx, args)

        elif operation == 'deploy':
            return deploy(ctx)

        else:
            return 'Unknown Operation'

def deploy():
    """
    :param token: Token The token to deploy
    :return:
        bool: Whether the operation was successful
    """
    if not CheckWitness(CONTRACT_OWNER):
        print("Must be owner to deploy")
        return False

    if not Get(ctx, 'initialized'):
        # do deploy logic
        Put(ctx, 'initialized', 1)
        Put(ctx, CONTRACT_OWNER, TOKEN_INITIAL_AMOUNT)
        Put(ctx, AD_COUNT_KEY, 0)
        return add_to_circulation(ctx, TOKEN_INITIAL_AMOUNT)

    return False


def get_default_content():
    return Get(ctx, DEFAULT_CONTENT_KEY)

def get_ad_count():
    return Get(ctx, AD_COUNT_KEY)

def update_board_round(board_id):
    # update ruond end date
    period = Get(ctx, get_period_key(board_id))
    round_end = GetTime() + period
    Put(ctx, get_endtime_key(board_id), round_end)
    # update owner to highest bidder
    new_owner = Get(ctx, get_highest_bidder_key(board_id))
    Put(ctx, get_owner_key(board_id), new_owner)
    # update content to new owner's content
    new_content = Get(ctx, get_next_content_key(board_id))
    Put(ctx, get_content_key(board_id), new_content)
    # Set highest bid to 0
    Put(ctx, get_highest_bid_key(board_id), 0)
    print('Update Round Completed')
    return True


def init_board_info(board_id, creator, period, domain_name):
    # Save Basic Info about a board: period, creator, domain_name
    Put(ctx, get_period_key(board_id), period)
    Put(ctx, get_ad_admin_key(board_id), creator)
    Put(ctx, get_domain_key(board_id), domain_name)
    # Put Default value into Board[Next Round]
    Put(ctx, get_highest_bid_key(board_id), 0)
    Put(ctx, get_highest_bidder_key(board_id), creator)
    default_content = get_default_content()
    Put(ctx, get_next_content_key(board_id), default_content)
    return True


def check_expired(board_id):
    board_end_timestamp = Get(ctx, get_endtime_key(board_id))
    if board_end_timestamp > GetTime():
        return False
    return True


def bid_for_board(board_id, bidder, bid, content):
    if bid <= 0:
        ''' and other value checking'''
        return False
    '''
    Check Balance
    '''
    # Bid is Valid
    highest_bid = Get(ctx, get_highest_bid_key(board_id))
    if bid > highest_bid:
        Put(ctx, get_highest_bid_key(board_id), bid)
        Put(ctx, get_highest_bidder_key(board_id), bidder)
        Put(ctx, get_next_content_key(board_id), content)
        return True

    else:
        print('Bid Smaller than Current Bid')
        return False

# Application Functions
def get_endtime(ctx, args):
    board_id = args[1]
    return Get(ctx, get_endtime_key(board_id))


def create_board(ctx, args):
    """
    args[0] := user_hash
    args[1] := domain name
    args[2] := bid round (second)
    """
    user_hash = args[0]
    domain_name = args[1]
    period = args[2]

    ad_count =  get_ad_count() + 1
    board_id = concat("NeonAD", ad_count)
    Put(ctx, AD_COUNT_KEY, ad_count)

    init_sucess = init_board_info(board_id, user_hash, period, domain_name)
    update_success = update_board_round(board_id)

    return board_id


def bid_for_ad(ctx, args):
    """
    args[1] := board ID
    args[2] := Bid (NEP)
    args[3] := Content
    """
    user_hash = args[0]
    board_id = args[1]
    bid = args[2]

    expired = check_expired(board_id)
    if expired:
        update_board_round()
        print('Going into next Round')

    content = args[3]
    if bid_for_board(board_id, user_hash, bid, content) == True:
        return 'Bid Placed'
    else:
        return 'Bid Failed'


def edit_content(ctx, args):
    """
    args[0] := user_hash
    args[1] := board ID
    args[2] := new content
    """
    user_hash = args[0]
    board_id = args[1]
    new_content = args[2]
    if user_hash != Get(ctx, get_owner_key(board_id)):
        print('User is not authenticated to edit content of this board')
        return False
    else:
        '''
        Some Other checks on the incoming content
        '''
        Put(ctx, get_content_key(board_id), new_content)
        return True


def set_default_content(ctx, args):
    if CheckWitness(CONTRACT_OWNER):
        print('test')
        ad_content = args[1]
        Put(ctx, DEFAULT_CONTENT_KEY, ad_content)
        return ad_content
    else:
        print('This Function can only be triggered by admin')
        return False
