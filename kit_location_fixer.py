import requests
import pandas as pd
import re
from bs4 import BeautifulSoup


def start_session():
    s = requests.session()
    main_url = "https://winery.mywinesense.com/login"
    target_url = "https://winery.mywinesense.com/session"
    response = s.get(main_url)
    soup = BeautifulSoup(response.content, features="html.parser")
    payload = {'email': 'brandon@mywinesense.com',
               'password': 'winery',
               'utf8': soup.find(attrs={'name': 'utf8'})['value'],
               'authenticity_token': soup.find(attrs={'name': 'authenticity_token'})['value']}
    response = s.post(target_url, data=payload)
    return(s, payload)


def grab_the_locations(s, payload):
    kitloc_url = "https://winery.mywinesense.com/kit_locations"
    kitlocresp = s.get(kitloc_url, data=payload)
    kitlocbowl = BeautifulSoup(kitlocresp.content, features="html.parser")
    # make two lists from the kit location page
    locationList = [kitloc.text for kitloc in kitlocbowl.find_all("div", {"class": "name"})]
    batchList = [batchnum.text for batchnum in kitlocbowl.find_all("div", {"class": "batch"})]
    loc_id_list = []
    for each in kitlocbowl.find_all('div', class_="location-container"):
        loc_id_list.append(each.find('div')['data-location-id'])

    # create a dataframe with the three lists of kits and locations
    kitdf = pd.DataFrame(
        {'Location': locationList,
         'BatchNum': batchList,
         'Loc_ID': loc_id_list
         })
    emptyListDF = kitdf[kitdf["BatchNum"]==""]
    empty_loc_list = emptyListDF["Location"].tolist()
    print(empty_loc_list)
    return(kitdf,empty_loc_list)


def valid_batch(batch_to_check):
    testbatch = kitdf.loc[kitdf['BatchNum'].str.contains(batch_to_check)]
    # print("TB", testbatch)
    if not testbatch.empty:
        return True
    else:
        return False


def validate_location(location_to_check):
    testloc = kitdf.loc[kitdf['Location'].str.contains(location_to_check)]
    # print(location_to_check, "LC", testloc)
    if not testloc.empty:
        return True
    else:
        return False


def get_batches_to_move():
    batch_from_file = []
    loc_from_file = []
    # grab variables from config file
    # cfgfile='/home/jason/PycharmProjects/BottlingInfo/venv/batchmoves.txt'
    cfgfile='c:\\users\\user\\desktop\\batchmoves.txt'
    move_counter = 0
    with open(cfgfile) as openfile:
        for line in openfile:
            # skip the empty lines
            if not line.strip():
                continue
            line = line.upper()
            # print("line:", line)
            matches = re.match(r'(\d{5}):([A-Z]-\d{1,3})', line)
            print("checking ", line.rstrip('\n'))
            if matches:
                if valid_batch(matches.group(1)):
                    print("...valid batch",matches.group(1))
                    if validate_location(matches.group(2)):
                        print("....valid location", matches.group(2))
                        print("adding to list")
                        batch_from_file.append(matches.group(1))
                        loc_from_file.append(matches.group(2))
                    move_counter = move_counter + 1
                else:
                    print("either batch number " + matches.group(1) + " does not exist at this store")
                # print(batch_from_file, loc_from_file)
            else:
                print(line, "didn't match a batch location combo .... get that garbage outta here")
    return(batch_from_file, loc_from_file, move_counter)


def get_app_loc_id(location_name):
    app_locDF = kitdf.loc[kitdf['Location'] == location_name]
    # print(testloc)
    location_result = app_locDF.Loc_ID.item()
    return(location_result)


def move_batch_to_location(batch_num_to_move, location_result):
    batch_page_url = "https://winery.mywinesense.com/batches/" + batch_num_to_move + "/edit"
    batch_page_resp = s.get(batch_page_url, data=payload)
    batch_page_bowl = BeautifulSoup(batch_page_resp.content, features="html.parser")
    payload.update({
        'utf8': batch_page_bowl.find(attrs={'name': 'utf8'})['value'],
        'authenticity_token': batch_page_bowl.find(attrs={'name': 'authenticity_token'})['value'],
    })
    for posresult in batch_page_bowl.find_all('input', {'type': 'text'}):
        pos = str(posresult)
        pos = pos.upper()
        # print(type(pos))
        if "CUSTOMER_KIT_POS_TRANSACTION_ID" in pos:
            customer_pos_grp = re.match(r'.*VALUE="([A-Z]{3}\d{4,7})".*', pos)
            customer_pos = customer_pos_grp[1]
            # print(customer_pos)
    for input_results in batch_page_bowl.find_all('input', {'type': 'hidden'}):
        in_res = str(input_results)
        # print(in_res)
        if 'customer_id' in in_res:
            in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
            this_customer_id = in_res_grp[1]
            # print(this_customer_id)
        if 'shrinks' in in_res:
            in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
            this_shrink = in_res_grp[1]
            # print(this_shrink)
        if 'reg_labels' in in_res:
            in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
            this_reg_labels = in_res_grp[1]
            # print(this_reg_labels)
        if 'cust_labels' in in_res:
            in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
            this_cust_labels = in_res_grp[1]
            # print(this_cust_labels)
    # grab Service Choice and id# for this batches current location
    for option_results in batch_page_bowl.find_all('option', {'selected': True}):
        opt_res = str(option_results)
        if ('Deluxe' in opt_res) or ('Intermediate' in opt_res) or ('Basic' in opt_res):
            opt_res_grp = re.match(r'.*value="([a-z]{4,14})"', opt_res)
            this_service_type = opt_res_grp[1]
            # print(this_service_type)
        # if we see a phone number, this is the customer id
        if re.search(r'([A-Z]-\d{1,3})', opt_res):
            # print(opt_res)
            in_opt_grp = re.match(r'.*value="(\d{1,6})".*', opt_res)
            this_location_id = in_opt_grp[1]
            # print(this_location_id)
    payload.update({'customer_kit[customer_id]': this_customer_id,
                    'customer_kit[pos_transaction_id]': customer_pos,
                    'customer_kit[kit_location]': location_result,
                    'customer_kit[winery_fee]': this_service_type,
                    'customer_kit[shrinks]': this_shrink,
                    'customer_kit[reg_labels]': this_reg_labels,
                    'customer_kit[cust_labels]': this_cust_labels,
                    '_method': 'patch',
                    'commit': 'Update Batch',
                    })
    print("moving " + batch_num_to_move)
    print(payload)
    # post the changes
    batch_page_post_url = "https://winery.mywinesense.com/batches/" + batch_num_to_move
    response = s.post(batch_page_post_url, data=payload)
    kitdf.loc[(kitdf['BatchNum'] == batch_num_to_move) , 'BatchNum'] = ''
    return()


s, payload = start_session()
kitdf, empty_loc_list = grab_the_locations(s, payload)
#print(kitdf)
batch_from_file, loc_from_file, num_moves = get_batches_to_move()

num_moves = num_moves + 20 # to offset the Zs

loc_needs_to_be_empty = []
for kit_to_move_loc in loc_from_file:
    if kit_to_move_loc not in empty_loc_list:
        print (kit_to_move_loc, " not in empty list")
        loc_needs_to_be_empty.append(kit_to_move_loc)
        batch_to_move = kitdf.loc[kitdf['Location'] == kit_to_move_loc, 'BatchNum'].iloc[0]
        print("we need to move: ", batch_to_move)
        empty_spot = empty_loc_list[-1]
        print("the empty spot is:", empty_spot)
        empty_loc_app_id = get_app_loc_id(empty_spot)
        move_batch_to_location(batch_to_move, empty_loc_app_id)
        empty_loc_list.remove(empty_spot)
    else:
        print(kit_to_move_loc, "in empty list - ready to move, delete location from empty list")
        empty_loc_list.remove(kit_to_move_loc)
print("loc list")
print(loc_needs_to_be_empty)
print("empty_loc_list")
print(empty_loc_list)

leftover_batches = []
leftover_locations = []
for batches_to_move_counter in range(len(loc_from_file)):
    # check loc for a batch is empty
    # if its empty, update batch location and remove it from the batch/location list
    testloc = kitdf.loc[kitdf['Location']==loc_from_file[batches_to_move_counter]]
    # print(testloc)
    location_result = testloc.Loc_ID.item()
    batch_result = testloc.BatchNum.item()
    # print(loc_from_file[batches_to_move_counter], "\nLC\n", testloc.Location.item())
    if not batch_result:
        batch_page_url = "https://winery.mywinesense.com/batches/" + str(batch_from_file[batches_to_move_counter]) + "/edit"
        batch_page_resp = s.get(batch_page_url, data=payload)
        batch_page_bowl = BeautifulSoup(batch_page_resp.content, features="html.parser")
        payload.update({
            'utf8': batch_page_bowl.find(attrs={'name': 'utf8'})['value'],
            'authenticity_token': batch_page_bowl.find(attrs={'name': 'authenticity_token'})['value'],
        })
        for posresult in batch_page_bowl.find_all('input', {'type': 'text'}):
            pos = str(posresult)
            pos = pos.upper()
            # print(type(pos))
            if "CUSTOMER_KIT_POS_TRANSACTION_ID" in pos:
                customer_pos_grp = re.match(r'.*VALUE="([A-Z]{3}\d{4,7})".*', pos)
                if customer_pos_grp:
                    # print(customer_pos_grp)
                    customer_pos = customer_pos_grp[1]
                else:
                    customer_pos = ''
                # print(customer_pos)
        for input_results in batch_page_bowl.find_all('input', {'type': 'hidden'}):
            in_res = str(input_results)
            # print(in_res)
            if 'customer_id' in in_res:
                in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
                this_customer_id = in_res_grp[1]
                # print(this_customer_id)
            if 'shrinks' in in_res:
                in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
                this_shrink = in_res_grp[1]
                # print(this_shrink)
            if 'reg_labels' in in_res:
                in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
                this_reg_labels = in_res_grp[1]
                # print(this_reg_labels)
            if 'cust_labels' in in_res:
                in_res_grp = re.match(r'.*value="(\d{1,6})".*', in_res)
                this_cust_labels = in_res_grp[1]
                # print(this_cust_labels)
        # grab Service Choice and id# for this batches current location
        for option_results in batch_page_bowl.find_all('option', {'selected': True}):
            opt_res = str(option_results)
            if ('Deluxe' in opt_res) or ('Intermediate' in opt_res) or ('Basic' in opt_res):
                opt_res_grp = re.match(r'.*value="([a-z]{4,14})"',opt_res)
                this_service_type = opt_res_grp[1]
                # print(this_service_type)
            # if we see a phone number, this is the customer id
            if re.search(r'([A-Z]-\d{1,3})', opt_res):
                # print(opt_res)
                in_opt_grp = re.match(r'.*value="(\d{1,6})".*', opt_res)
                this_location_id = in_opt_grp[1]
                # print(this_location_id)
        payload.update({'customer_kit[customer_id]': this_customer_id,
                        'customer_kit[pos_transaction_id]': customer_pos,
                        'customer_kit[kit_location]': location_result,
                        'customer_kit[winery_fee]': this_service_type,
                        'customer_kit[shrinks]': this_shrink,
                        'customer_kit[reg_labels]': this_reg_labels,
                        'customer_kit[cust_labels]': this_cust_labels,
                        '_method': 'patch',
                        'commit': 'Update Batch',
                        })
        print("moving " + str(batch_from_file[batches_to_move_counter]))
        # print(payload)
        # post the changes
        batch_page_post_url = "https://winery.mywinesense.com/batches/" + str(batch_from_file[batches_to_move_counter])
        try:
            response = s.post(batch_page_post_url, data=payload)
        except requests.exceptions.RequestException as e:
            print(e)
    else:
        print("lc wasnt empty for batch " + str(batch_from_file[batches_to_move_counter]))
        leftover_batches.append(batch_from_file[batches_to_move_counter])
        leftover_locations.append(loc_from_file[batches_to_move_counter])

print("and then end is")
# print(batch_from_file, loc_from_file)
for x in range(len(leftover_batches)):
    print(leftover_batches[x] + ":" + leftover_locations[x])



