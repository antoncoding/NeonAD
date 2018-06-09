from boa.interop.Neo.Runtime import CheckWitness, Log, GetTime, GetTrigger, Serialize, Deserialize
from boa.interop.Neo.Storage import GetContext, Put, Delete, Get
from boa.interop.Neo.Action import RegisterAction
from boa.interop.Neo.Blockchain import GetHeader, GetHeight
from boa.interop.Neo.Header import GetTimestamp
from boa.interop.Neo.TriggerType import Application, Verification

from boa.builtins import concat
# Key retreival functions Definition
from util import *
# ICO Template
from nad.txio import get_asset_attachments
from nad.token import *
from nad.crowdsale import *
from nad.nep5 import *


OnTransfer = RegisterAction('transfer', 'addr_from', 'addr_to', 'amount')
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
        return can_exchange(ctx, attachments, verify_only=True)

    # Main Application Operation
    elif trigger == Application():
        for op in NEP5_METHODS:
            if operation == op:
                return handle_nep51(ctx, operation, args)

        # Functions that can be called by anyone
        if operation == "getBoardList":
            return get_board_list()

        elif operation == "getContent":
            return get_content(ctx, args)

        elif operation == "getRoundInfo":
            return get_round_info(ctx, args)

        elif operation == "getEndTime":
            return get_endtime(ctx,args)

        # ICO crowdsale function
        elif operation == 'circulation':
            return get_circulation(ctx)

        # # Main Operations on SC
        # # Functions that Require Authorization
        user_hash = args[0]
        authorized = CheckWitness(user_hash)
        if not authorized:
            return 'CheckWitness Failed'
        Log("Authorized")

        if operation == "createBoard":
            return create_board(ctx, args)

        elif operation == "bidForBoard":
            return bid_for_board(ctx, args)

        elif operation == "editContent":
            return edit_content(ctx, args)

        elif operation == "editPeriod":
            return edit_period(ctx, args)

        # Functions Only Available from Contract Owner
        elif operation == "setDefaultContent":
            return set_default_content(ctx, args)

        elif operation == 'deploy':
            return deploy(ctx)

        # ICO related
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


        else:
            return 'Unknown Operation'

def deploy():
    """
    :param token: Token The token to deploy
    :return:
        bool: Whether the operation was successful
    """
    if not CheckWitness(CONTRACT_OWNER):
        return "Must be owner to deploy"

    if not Get(ctx, 'initialized'):
        # do deploy logic
        Put(ctx, 'initialized', 1)
        Put(ctx, AD_LIST_KEY, Serialize([]))
        Put(ctx, CONTRACT_OWNER, TOKEN_INITIAL_AMOUNT)
        # Set ICO Start and end date
        height = GetHeight()
        Put(ctx, BLOCK_SALE_START_KEY, height)
        Put(ctx, BLOCK_SALE_LIMIT_END_KEY, height + ICO_LIMITED_DURATION)

        return add_to_circulation(ctx, TOKEN_INITIAL_AMOUNT)

    return 'Deploy Failed'


def get_default_content():
    return Get(ctx, DEFAULT_CONTENT_KEY)


def get_ad_count():
    serialized_list = Get(ctx, AD_LIST_KEY)
    if not serialized_list:
        return 0

    board_list = Deserialize(serialized_list)
    return len(board_list)


def get_board_list():
    serialized_list = Get(ctx, AD_LIST_KEY)
    board_list = Deserialize(serialized_list)
    if len(board_list) == 0:
        return ''
    return_str = ""
    for _id in board_list:
        print(_id)
        return_str = concat(return_str, _id)
        return_str = concat(return_str, ",")
    return return_str


def get_content(ctx, args):
    if len(args)==2:
        board_id = args[1]
        return Get(ctx, get_content_key(board_id))


def add_new_board(board_id):
    serialized_list = Get(ctx, AD_LIST_KEY)
    board_list = Deserialize(serialized_list)
    board_list.append(board_id)
    serizlized_list = Serialize(board_list)
    Put(ctx, AD_LIST_KEY, serizlized_list)
    return 'Successfully Created  '

def check_board_exist(board_id):
    serialized_list = Get(ctx, AD_LIST_KEY)
    board_list = Deserialize(serialized_list)
    for _id in board_list:
        if _id == board_id:
            return True
    return False

def update_board_round(board_id):
    # update ruond end date

    payment = Get(ctx, get_highest_bid_key(board_id))
    board_admin = Get(ctx, get_ad_admin_key(board_id))
    # pay web owner
    if payment > 0:
        success = pay_in_token(ctx, CONTRACT_OWNER, board_admin, payment)
        if not success:
            return False

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


def init_board_info(board_id, creator, period, domain_name, stack):
    # Save Basic Info about a board: period, creator, domain_name
    Put(ctx, get_period_key(board_id), period)
    Put(ctx, get_ad_admin_key(board_id), creator)
    Put(ctx, get_domain_key(board_id), domain_name)
    Put(ctx, get_stack_key(board_id), stack)
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


def do_bid(board_id, bidder, bid, content):
    if bid <= 0:
        return False

    # Bid is Valid
    highest_bid = Get(ctx, get_highest_bid_key(board_id))
    if bid > highest_bid:

        # pay to system
        payment_success = pay_in_token(ctx, bidder, CONTRACT_OWNER, bid)
        if payment_success == False:
            print('Bid failed')
            return False

        # refund last bidder
        last_bidder = Get(ctx, get_highest_bidder_key(board_id))
        refund_success = pay_in_token(ctx, CONTRACT_OWNER, last_bidder, highest_bid)

        Put(ctx, get_highest_bid_key(board_id), bid)
        Put(ctx, get_highest_bidder_key(board_id), bidder)
        Put(ctx, get_next_content_key(board_id), content)
        return True

    else:
        print('Bid Smaller than Current Bid')
        return False

# Application Functions
def get_endtime(ctx, args):
    if len(args) == 2:
        board_id = args[1]
        if not check_board_exist(board_id):
            return False

        return Get(ctx, get_endtime_key(board_id))


def create_board(ctx, args):
    """
    args[0] := user_hash
    args[1] := domain name
    args[2] := bid round (second)
    args[3] := nad token to stack
    """
    if len(args) == 4:
        user_hash = args[0]
        domain_name = args[1]
        period = args[2]
        stack_token = args[3]

        board_id = GetTime() + get_ad_count()

        if check_board_exist(board_id):
            return 'board creation ID error, Please try again later.'
        # Stack NAD token to get Listed
        if pay_in_token(ctx, user_hash, CONTRACT_OWNER, stack_token):
            init_sucess = init_board_info(board_id, user_hash, period, domain_name, stack_token)
            add_success = add_new_board(board_id)
            update_success = update_board_round(board_id)

            return board_id

        return 'insufficient NAD token to stack'

def bid_for_board(ctx, args):
    """
    args[0] := user_hash
    args[1] := board ID
    args[2] := Bid (NEP)
    args[3] := Content
    """
    if len(args) ==4:
        user_hash = args[0]
        board_id = args[1]
        if not check_board_exist(board_id):
            print('boad id error')
            return False
        bid = args[2]
        expired = check_expired(board_id)
        if expired:
            success = update_board_round(board_id)
            if success:
                print('Going into next Round')
            else:
                print('Update Round Error')
                return False

        content = args[3]
        if do_bid(board_id, user_hash, bid, content) == True:
            return 'Bid Placed'

    return 'Bid Failed'


def edit_content(ctx, args):
    """
    args[0] := user_hash
    args[1] := board ID
    args[2] := new content
    """
    if len(args) == 3:
        user_hash = args[0]
        board_id = args[1]
        new_content = args[2]
        if not check_board_exist(board_id):
            return False

        if user_hash != Get(ctx, get_owner_key(board_id)):
            print('User is not authenticated to edit content of this board')
            return False
        else:
            '''
            Some Other checks on the incoming content
            '''
            Put(ctx, get_content_key(board_id), new_content)
            return True


def edit_period(ctx, args):
    """
    args[0] := user_hash
    args[1] := board ID
    args[2] := new_period
    """
    if len(args) == 3:
        user_hash = args[0]
        board_id = args[1]
        new_period = args[2]
        if not check_board_exist(board_id):
            return False

        if user_hash != Get(ctx, get_owner_key(board_id)):
            print('User is not authenticated to edit content of this board')
            return False
        else:
            '''
            Some Other checks on new bidding round period
            '''
            if new_period > 1200:
                Put(ctx, get_period_key(board_id), new_period)
                return True

        return False


def get_round_info(ctx, args):
    '''
    args[0] := user_hash
    args[1] := board ID
    return: serialized_map
    '''
    # return False
    board_id = args[1]
    if not check_board_exist(board_id):
        return 'Error:board id not found.'
    endtime = Get(ctx, get_endtime_key(board_id))
    highest_bidder = Get(ctx, get_highest_bidder_key(board_id))
    highest_bid = Get(ctx, get_highest_bid_key(board_id))
    rd = {"endtime":endtime, "highest_bid":highest_bid, "highest_bidder":highest_bidder}
    return Serialize(rd)


def set_default_content(ctx, args):
    if CheckWitness(CONTRACT_OWNER) and len(args)==2:
        print('test')
        ad_content = args[1]
        Put(ctx, DEFAULT_CONTENT_KEY, ad_content)
        return 'Successfully Update Default Content'

    else:
        return 'This Function can only be triggered by admin'


def pay_in_token(ctx, t_from, t_to, amount):
    if amount <= 0:
        return False
    if len(t_to) != 20:
        return False
    if t_from == t_to:
        print("transfer to self!")
        return True

    from_balance = Get(ctx, t_from)
    if from_balance < amount:
        print("insufficient funds")
        return False
    elif from_balance == amount:
        Delete(ctx, t_from)
    else:
        difference = from_balance - amount
        Put(ctx, t_from, difference)

    to_balance = Get(ctx, t_to)
    to_total = to_balance + amount
    Put(ctx, t_to, to_total)

    OnTransfer(t_from, t_to, amount)

    return True
