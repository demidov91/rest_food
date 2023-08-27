from enum import Enum


class SupplyState(Enum):
    READY_TO_POST = 'ready_to_post'
    POSTING = 'posting'
    SET_TIME = 'set_time'
    VIEW_INFO = 'view_info'
    EDIT_NAME = 'edit_name'
    EDIT_ADDRESS = 'edit_address'
    EDIT_COORDINATES = 'edit-coordinates'
    EDIT_PHONE = 'edit_phone'
    FORCE_NAME = 'force_name'
    FORCE_ADDRESS = 'force_address'
    FORCE_COORDINATES = 'force_coordinates'
    INITIAL_EDIT_PHONE = 'initial_edit_phone'
    BOOKING_CANCEL_REASON = 'booking_cancel_reason'
    NO_STATE = 'no_state'


class DemandState(Enum):
    EDIT_NAME = 'edit_name'
    EDIT_PHONE = 'edit_phone'
    EDIT_SOCIAL_STATUS = 'edit_social_status'


class Provider(Enum):
    TG = 'telegram'
    VB = 'viber'


class Workflow(Enum):
    SUPPLY = 'supply'
    DEMAND = 'demand'


class SocialStatus(Enum):
    BIG_FAMILY = 'big_family'
    DISABILITY = 'disability'
    HOMELESS = 'homeless'
    HARD_TIMES = 'hard_times'
    EMIGRANT = 'emigrant'
    OTHER = 'other'


class DemandCommand(Enum):
    """*Demand* bot commands in a format: {command}|{arg_0}|...|{arg_n}"""
    TAKE = 'take'
    INFO = 'info'
    SHORT_INFO = 'sinf'
    DISABLE_USERNAME = 'disable-username'
    ENABLE_USERNAME = 'enable-username'
    EDIT_NAME = 'edit_name'
    EDIT_PHONE = 'edit_phone'
    EDIT_SOCIAL_STATUS = 'edit_ss'
    SET_SOCIAL_STATUS = 'set_ss'
    FINISH_TAKE = 'f_take'
    BOOKED = 'bkd'
    MAP_INFO = 'mapi'
    MAP_TAKE = 'mapt'
    MAP_BOOKED = 'mapb'

    def build(self, *args):
        return '|'.join((self.value, ) + args)


class SupplyCommand(Enum):
    """*Supply* bot commands in a format: c|{command}|{arg_0}|...|{arg_n}"""
    CANCEL_BOOKING = 'cancel_booking'
    APPROVE_BOOKING = 'approve_booking'
    BACK_TO_POSTING = 'back_to_posting'
    LIST_MESSAGES = 'list_messages'
    SHOW_DEMANDED_MESSAGE = 'sdm'
    SHOW_NON_DEMANDED_MESSAGE = 'show_ndm'
    APPROVE_SUPPLIER = 'approve_supplier'
    DECLINE_SUPPLIER = 'decline_supplier'

    def build(self, *args):
        return '|'.join(('c', self.value) + args)


class TgCommand(Enum):
    """Expected enum of Telegram /{command}s """
    START = 'start'
    LANGUAGE = 'language'
    LOCATION = 'location'


class UserInfoField(Enum):
    # tg/viber username
    USERNAME = 'username'
    # supply place name
    NAME = 'name'
    # supply address
    ADDRESS = 'address'
    # supply coordinates
    COORDINATES = 'coordinates'
    # contact phone
    PHONE = 'phone'
    # True if the user has shared their username
    DISPLAY_USERNAME = 'display_username'
    # Bot language for this user.
    LANGUAGE = 'language'
    # True for approved coordinates (rather than proposed by system)
    IS_APPROVED_COORDINATES = 'is_approved_coordinates'
    # If the user has explicitly approved specified `LANGUAGE` (rather than set by messeger client language)
    IS_APPROVED_LANGUAGE = 'is_approved_language'
    # demand-side-chosen social status
    SOCIAL_STATUS = 'social_status'
    # True for supply users who are allowed to post messages. Actually it makes sense to move it into the User level...
    IS_APPROVED_SUPPLY = 'is_approved_supply'
