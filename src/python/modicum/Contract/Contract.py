import logging
import os
import importlib
from binascii import unhexlify, hexlify
from .. import helper
from web3.datastructures import AttributeDict
from web3 import Web3
from hexbytes import HexBytes

def maybe_hex(x):
    if isinstance(x, HexBytes):
        return x.hex()
    else:
        return x

class Contract:
    def __init__(self, client, address, events):
        self.logger = logging.getLogger("Contract")
        self.logger.setLevel(logging.INFO)

        # if the DEBUG environment variable is set, then set the logger to debug
        if os.environ.get("DEBUG") is not None:
            self.logger.setLevel(logging.DEBUG)
        
        # ch = logging.StreamHandler()
        # formatter = logging.Formatter("---%(name)s---: \n%(message)s\n\r")
        # ch.setFormatter(formatter)
        # self.logger.addHandler(ch)

        self.client = client  # instance of EthereumClient
        self.address = address  # Ethereum contract address
        self.filter_id = client.new_filter() # 7/2/2019 could use self.client.filter_id instead. 
        self.func_hash = {}
        self.generate_topics(events)

    def encode_address(address):
        return "000000000000000000000000" + address[2:]

    def encode_uint(value):
        return format(value, "064x")

    def encode_int(value):
        return format(value & 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff, "064x")

    def encode_bool(value):
        return Contract.encode_uint(1 if value else 0)

    def encode_bytes32(value):
        # print("value: %s" %value)
        bytesvalue = value.encode()
        hexstr = hexlify(bytesvalue).decode("utf-8")
        bytes32 = hexstr.ljust(64,'0')
        return bytes32

    def encode_string(value):
        bytesvalue = value.encode('utf-8')
        hexstr = hexlify(bytesvalue).decode("utf-8")
        p1 = "00000000000000000000000000000000000000000000000000000000000000c0"
        p2 = "0000000000000000000000000000000000000000000000000000000000000040"
        p3 = hexstr.ljust(64, '0')
        return (p1 + p2 + p3)

    def decode_address(data, pos):
        return "0x" + data[pos * 64 + 24: (pos + 1) * 64]

    def decode_uint(data, pos):
        return int(data[pos * 64: (pos + 1) * 64], 16)

    def decode_int(data, pos):
        uint = Contract.decode_uint(data, pos)
        if uint > 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff:
            uint -= 0x10000000000000000000000000000000000000000000000000000000000000000
        return uint

    def decode_bool(data, pos):
        uint = Contract.decode_uint(data, pos)
        if uint == 1:
            return True
        elif uint == 0:
            return False
        raise Exception("Unexpected boolean value {}".format(uint))

    def decode_bytes32(data, pos):
        string = bytearray.fromhex(data[pos * 64: (pos + 1) * 64]).decode()
        return string.strip('\x00')

    def decode_string(data, pos):
        logging.warning("decode_string function is broken, beware! pos parameter is not used")
        n = 64
        # Split the data into 64 bit arrays
        arrays = [data[i:i + n] for i in range(0, len(data), n)]
        string = ""  # the string

        for array in arrays:
            print(array)
            if array[0] != "0":
                try:
                    string += unhexlify(array).decode('utf-8')
                except UnicodeDecodeError as e:
                    logging.debug("Not a string")

        # -----------Below doesn't get the dubug string---------------
        #   start = False #tracks start staring 64 chars ending with c0
        #   size = 0 #tracks value after start value, which is the size of the string
        #
        #   #iterate through the arrays
        #   for array in arrays:
        #       print("Contract.py")
        #       print(unhexlify(array))
        #       #check if the size of the string is known, because if it is then this array is part of it
        #       if size:
        #           string += unhexlify(array).decode('utf-8')
        #       #check if the start array has passed, because if it has this is the size array
        #       if start and not size:
        #           size = int(array,32)
        #       # Check if this is the start array
        #       if "c0".zfill(64) in array:
        #           start = True
        return string.strip('\x00')

    def generate_topics(self, events):
        self.topics = {}
        for event in events:
            name = event
            topic = {'name': name}
            params = []
            for param in events[event]:
                ptype = param[1]
                pname = param[0]
                params.append((ptype, pname))
            topic['params'] = params

            # This part, converts enums to uint8 for checking signature hash.
            params = params.copy()
            for i in range(0, len(params)):
                if Contract.is_enum_defined(params[i][0]):
                    params[i] = ('uint8', params[i][1])

            signature = "{}({})".format(name, ",".join([ptype for (ptype, pname) in params]))
            keccak256 = self.client.keccak256(signature)
            if not (keccak256.startswith("0x") and len(keccak256) == 66):
                raise Exception("Incorrect hash {} computed for signature {}!".format(keccak256, signature))
            self.topics[keccak256] = topic
        return self.topics

    def call_func(self, from_account, getReceipt, price, name, *args):
    # def call_func(self, from_account, getReceipt, price, name, aix, oid, ijoid, *args):
        # generate signature
        arg_types = []
        arg_values = []
        for i in range(len(args) >> 1):
            arg_types.append(args[i * 2])
            arg_values.append(args[i * 2 + 1])

        # This part, converts enums to uint8 for checking signature hash.
        # TODO I'm not sure if it works!!
        arg_types_signature = arg_types.copy()
        for i in range(0, len(arg_types_signature)):
            if Contract.is_enum_defined(arg_types_signature[i]):
                arg_types_signature[i] = 'uint8'
        # End part!

        signature = "{}({})".format(name, ",".join(arg_types_signature))
        if signature not in self.func_hash:
            keccak256 = self.client.keccak256(signature)
            if not (keccak256.startswith("0x") and len(keccak256) == 66):
                raise Exception("Incorrect hash {} computed for signature {}!".format(keccak256, signature))
            self.func_hash[signature] = keccak256[:10]
        data = self.func_hash[signature]
        # encode arguments
        for i in range(len(arg_types)):
            # if arg_types[i] == "uint64":
            #     data += Contract.encode_uint(arg_values[i])
            # elif arg_types[i] == "uint256":
            #     data += Contract.encode_uint(arg_values[i])
            self.logger.debug("argtype: %s, argvalue: %s" %(arg_types[i], arg_values[i]))
            if "uint" in arg_types[i]:
                data += Contract.encode_uint(arg_values[i])
            elif arg_types[i] == "int64":
                data += Contract.encode_int(arg_values[i])
            elif arg_types[i] == "address":
                data += Contract.encode_address(arg_values[i])
            elif arg_types[i] == "bool":
                data += Contract.encode_bool(arg_values[i])
            elif arg_types[i] == "bytes32":
                data += Contract.encode_bytes32(arg_values[i])
            elif arg_types[i] == "string":
                data += Contract.encode_string(arg_values[i])
            elif Contract.is_enum_defined(arg_types[i]):
                this_enum = Contract.get_enum_by_classname(arg_types[i])
                this_member = arg_values[i]
                self.logger.debug("this_enum: %s" %this_enum)
                self.logger.debug("this_member: %s" %this_member)
                member_value = this_enum[this_member].value
                self.logger.debug("member_value: %s" %member_value)
                data += Contract.encode_int(member_value)
                # data += Contract.encode_int(Contract.get_enum_by_classname(arg_types[i])(arg_values[i]).value)
            else:
                raise NotImplementedError("Unknown type {}!".format(arg_types[i]))
        # send transaction
        self.logger.info("%s call: %s" %(from_account, name))

        exitcode = self.client.transaction(from_account, data, hex(price), self.address)
        if exitcode.startswith("0x"): 
            receipt = helper.wait4receipt(self.client,exitcode,getReceipt=getReceipt)
            self.logger.info("%s gasUsed: %s" %(name,receipt['gasUsed']))
            self.logger.info("%s cumulativeGasUsed: %s" %(name,receipt['cumulativeGasUsed']))

        return exitcode

    def poll_events(self):
        log = self.client.get_filter_changes(self.filter_id)
        events = []
        for item in log:
            if not isinstance(item, dict) and not isinstance(item, AttributeDict):
                self.logger.info(f"[poll_events] Skipping processing {item} since it is not a dict")
                continue
            if self.address == item['address']:
                if maybe_hex(item['topics'][0]) in self.topics:
                    topic = self.topics[maybe_hex(item['topics'][0])]
                    event_name = topic['name']
                    zs = [x for x in self.client.abi if x["type"] == "event" and x["name"] == event_name]
                    if len(zs) != 1:
                        raise Exception('oh no the universe exploded')
                    event_abi = zs[0]
                    from web3 import _utils
                    raw_event = dict(_utils.events.get_event_data(self.client.w3.codec, event_abi, item))
                    raw_event["params"] = raw_event["args"]
                    raw_event["name"] = event_name
                    del raw_event["args"]
                    events.append(raw_event)

        return events

    @staticmethod
    def is_enum_defined(name):
        try:
            module = importlib.import_module('..Enums',__name__)
            getattr(module, name)
            return True
        except AttributeError:
            return False

    @staticmethod
    def get_enum_by_classname(name):
        module = importlib.import_module('..Enums',__name__)
        return getattr(module, name)
