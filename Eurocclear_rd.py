from otto_cats_entry.catype.generate_ca_track_id import generate_caid_auto
from utils.base_file_processing import BaseClass
from utils.base_file import BaseClass
from subprocess import Popen
import time
from datetime import datetime, date, timedelta
from dateutil.parser import parse
import random
import traceback
import pandas as pd
import re
import requests
import json
import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(Path(file).resolve().parent.parent))


def periodic_coupon_rate_fun(select_data_caoption, row):
    try:
        raw_value = select_data_caoption.get("92F_INTP", "")
        if raw_value:
            # raw_value = "USD21,159"
            row["Periodic_Coupon_Rate"] = str(
                (float(raw_value[3:].replace(",", ".")) / 1000) * 100)[:6]
            # CATS-666 : Condition added on 10/03/2026 to Coupon_Payment_Amount
            row["Coupon_Payment_Amount"] = str(float(raw_value[3:].replace(
                ",", "."))) if raw_value[-1] != ',' else str(int(float(raw_value[3:].replace(",", "."))))
    except Exception as E:
        base_obj.logger.info(f"Error Occured in periodic_coupon_rate_fun - {E}")
    return row


def date_format_Change(datestring):
    try:
        if datestring == 'ONGO':
            date_values = ''
            # date_values = datetime.strptime(str(datestring),
            # "%Y%m%d").strftime("%Y-%m-%d %T")
        else:
            date_values = datetime.strptime(
                str(datestring),
                "%Y%m%d").strftime("%Y-%m-%d %H:%M:%S")
    except:
        pass

    return date_values


def chan_70_name_populate(row):

    targetname_list = []
    raw_entityname_list = []
    rejection_chan = ''
    raw_entityname_ferogs = ''
    raw_entityname = str(row.get('EntityName', '').strip())
    targetname = str(row.get('NAME_70E', '').strip())
    if targetname != '':

        if ' ' in targetname:
            targetname_list = targetname.split(' ')

        if raw_entityname != '' and ' ' in raw_entityname:
            raw_entityname_list = raw_entityname.split(' ')

        if len(targetname_list) >= 2 and len(raw_entityname_list) >= 2:
            if '%'.join(targetname_list).lower() != '%'.join(
                    raw_entityname_list).lower():
                raw_targetname_select = FERACK.fetchArray_withKey(
                    f''' SELECT TOP 1 EntityID, EntityName FROM FE.fe.feorgs WHERE EntityName like '%{
                        '%'.join(targetname_list).lower()}%' ''')

                if len(raw_targetname_select) != 0:
                    raw_entityname_ferogs = raw_targetname_select[0].get(
                        'EntityID', '')
                else:
                    rejection_chan = 'Rejected -  CHAN 70_NAME the new targetname not in FEORGS'
            else:
                rejection_chan = 'Rejected -  CHAN 70_NAME the new targetname and Feorgs Entityname is same.'

        elif targetname != '' and len(targetname_list) == 0:
            raw_entityname_select = FERACK.fetchArray_withKey(
                f''' SELECT TOP 1 EntityID, EntityName FROM FE.fe.feorgs WHERE EntityName like '{targetname}' ''')

            if len(raw_entityname_select) != 0:
                raw_entityname_ferogs = raw_entityname_select[0].get(
                    'EntityID', '')
            else:
                rejection_chan = 'Rejected -  CHAN 70_NAME the new targetname not in FEORGS'
    else:
        rejection_chan = 'Rejected - CHAN 22F_CHAN is Blank'

    return raw_entityname_ferogs, rejection_chan


def meeting_place_fun(row, cats_dict):

    if row.get('rawcatype', '') == 'BMET':
        if row.get('Meeting_Place', ''):
            cats_dict['Meeting_Place'] = row.get('Meeting_Place', '')
        else:
            cats_dict['Meeting_Place'] = "Undisclosed"
    else:
        cats_dict['Meeting_Place'] = ''

    return row, cats_dict

# test comment
def announcedate_fun(row, cats_dicta):

    #! Announcedate Logic
    if row.get(
        'rawcatype',
        ''
    ) in (
        'REDM',
        'BIDS',
        'CHAN',
        'CONS',
        'CONV',
        'DFLT',
        'EXOF',
        'PINK'
    ):
        if row.get(
            'announcedate_Redem',
            ''
        ).strip() != '' and len(
            row.get(
                'announcedate_Redem',
                ''
            )
        ) > 8:
            cats_dict['announcedate'] = datetime.strptime(row.get('announcedate_Redem', '')[
                :8], "%Y%m%d").strftime("%Y-%m-%d %T")
        else:
            cats_dict['announcedate'] = (
                date.today() -
                timedelta(
                    days=1)).strftime("%Y-%m-%d %T")
# comment 2
    elif len((row.get('FilePath', '').split("\\")[-1]).split('.')[1][:-2]) == 8:

        cats_dict['announcedate'] = datetime.strptime((row.get('FilePath', '').split(
            "\\")[-1]).split('.')[1][:-2], "%Y%m%d").strftime("%Y-%m-%d %T")
    else:
        cats_dict['announcedate'] = (date.today() -
                                     timedelta(days=1)).strftime("%Y-%m-%d %T")

    return row, cats_dict


def effectivedate_fun(row, cats_dict, select_data_caoption):

    ##! effectivedate logic
    effectivedate = ''

    if row.get('rawcatype', '') in (
        'DFLT'
    ):  # removed BIDS it need to capture effective date 25/07/24
        cats_dict['effectivedate'] = ''
        effectivedate = ''

    elif row.get('rawcatype', '') == 'BMET':
        if row.get('effectivedate_MEET_C', '') != '':
            cats_dict['effectivedate'] = datetime.strptime(
                str(row.get('effectivedate_MEET_C', '')[:8]), "%Y%m%d").strftime("%Y-%m-%d %T")
            effectivedate = datetime.strptime(str(row.get('effectivedate_MEET_C', '')[
                :8]), "%Y%m%d").strftime("%d-%b-%Y")

        elif row.get('effectivedate_MEET_A', '') != '':
            cats_dict['effectivedate'] = datetime.strptime(
                str(row.get('effectivedate_MEET_A', '')[:8]), "%Y%m%d").strftime("%Y-%m-%d %T")
            effectivedate = datetime.strptime(str(row.get('effectivedate_MEET_A', '')[
                :8]), "%Y%m%d").strftime("%d-%b-%Y")
        else:
            cats_dict['effectivedate'] = ''
            effectivedate = ''
            row['Comments'] = 'Effective Date is Blank'

    elif row.get('rawcatype', '') == 'CONS' or row.get('rawcatype', '') == 'DTCH':
        if select_data_caoption:  # condition newly added on 25/07/24
            try:
                cats_dict['effectivedate'] = datetime.strptime(str(select_data_caoption.get(
                    'ca_effectivedate_VALU', '')), "%Y%m%d").strftime("%Y-%m-%d %T")
            except:
                pass

            if cats_dict['effectivedate'] == '' and row.get(
                'effectivedate_CONS', ''
            ) != '' and row.get(
                'rawcatype', ''
            ) == 'CONS':
                cats_dict['effectivedate'] = datetime.strptime(
                    str(row.get('effectivedate_CONS', '')), "%Y%m%d").strftime("%Y-%m-%d %T")
            if row.get('effectivedate_CONS', '') != '':
                row["ResultDate"] = datetime.strptime(
                    str(row.get('effectivedate_CONS', '')), "%Y%m%d").strftime("%Y-%m-%d %T")
        else:
            cats_dict['effectivedate'] = ''
            effectivedate = ''
            row['Comments'] = 'Effective Date is Blank'

    elif row.get('rawcatype', '') in ('EXTM', 'CHAN') and str(row.get('effectivedate_EXTM', '')) != '':
        cats_dict['effectivedate'] = datetime.strptime(
            row.get('effectivedate_EXTM', ''), "%Y%m%d").strftime("%Y-%m-%d %T")
        effectivedate = datetime.strptime(
            row.get(
                'effectivedate_EXTM',
                ''
            ),
            "%Y%m%d").strftime("%d-%b-%Y")

    elif str(row.get('effectivedate_PAYD', '')) != '':
        cats_dict['effectivedate'] = datetime.strptime(
            str((row.get('effectivedate_PAYD', ''))), "%Y%m%d").strftime("%Y-%m-%d %T")
        effectivedate = datetime.strptime(
            cats_dict.get(
                'effectivedate',
                ''
            ),
            "%Y-%m-%d %H:%M:%S").strftime("%d-%b-%Y")

    elif select_data_caoption != '' and str(select_data_caoption.get('ca_effectivedate_PAYD', '')) != '' and ',' not in select_data_caoption.get('ca_effectivedate_PAYD', ''):
        cats_dict['effectivedate'] = datetime.strptime(str((select_data_caoption.get(
            'ca_effectivedate_PAYD', ''))), "%Y%m%d").strftime("%Y-%m-%d %T")
        effectivedate = datetime.strptime(
            cats_dict.get(
                'effectivedate',
                ''
            ),
            "%Y-%m-%d %H:%M:%S").strftime("%d-%b-%Y")

    elif select_data_caoption != '' and str(select_data_caoption.get('ca_effectivedate_VALU', '')) != '':
        cats_dict['effectivedate'] = datetime.strptime(str((select_data_caoption.get(
            'ca_effectivedate_VALU', ''))), "%Y%m%d").strftime("%Y-%m-%d %T")
        effectivedate = datetime.strptime(
            cats_dict.get(
                'effectivedate',
                ''
            ),
            "%Y-%m-%d %H:%M:%S").strftime("%d-%b-%Y")

    else:
        cats_dict['effectivedate'] = ''
        effectivedate = ''
        row['Comments'] = 'Effective Date is Blank'

    if row.get(
        'rawcatype',
        ''
    ) == 'EXTM' and str(
        row.get(
            'effectivedate_EXTM',
            ''
        )
    ) == '':
        row['Comments'] = 'Effective Date is Blank'

    return row, cats_dict, effectivedate


def add_space_between_text_and_number(text):

    text = text.replace(",", ".")
    if text[-1] == '.':
        text = text[:-1]
    # Define a regular expression pattern to find text followed by numbers
    pattern = re.compile(r'([a-zA-Z]+)(\d+)')
    # Use sub() function to replace matches with the modified string
    result = pattern.sub(r'\1 \2', text)
    return result

# Additional Column Added on 29 - Apr - 2024 as per the requirement on 26 - Apr - 2024


def additional_column_fun(row, cats_dict, select_data_caoption):

    print(row)
    if row.get('rawcatype', '') in ('BIDS', 'TEND', 'DTCH'):
        cats_dict['Maximum_Tender_Amount'] = row.get('Maximum_Tender_Amount', '')

        if row.get('Minimum_Tender_Amount_B', '') != '':
            cats_dict['Minimum_Tender_Amount'] = row.get(
                'Minimum_Tender_Amount_B', '')
        elif row.get('Minimum_Tender_Amount_C', '') != '':
            cats_dict['Minimum_Tender_Amount'] = row.get(
                'Minimum_Tender_Amount_C', '')
        else:
            cats_dict['Minimum_Tender_Amount'] = ''

        if (select_data_caoption.get('Early_Tender_consideration', '')).strip(
        ) != '' and '/' in select_data_caoption.get('Early_Tender_consideration', ''):
            cats_dict['Early_Tender_Consideration'] = add_space_between_text_and_number(
                select_data_caoption.get('Early_Tender_consideration', '').split("/")[1])
        else:
            cats_dict['Early_Tender_Consideration'] = ''

    if row.get('rawcatype', '') in ('CONV', 'EXOF'):
        if (select_data_caoption.get('NEWO_N', '')).strip(
        ) != '' and '/' in select_data_caoption.get('NEWO_N', ''):
            newon1 = add_space_between_text_and_number(
                select_data_caoption.get('NEWO_N', '').split("/")[0])
            newon2 = add_space_between_text_and_number(
                select_data_caoption.get('NEWO_N', '').split("/")[1])
            cats_dict['New_to_Old_Ratio'] = newon1 + "/" + newon2
        elif (select_data_caoption.get('NEWO_L', '')).strip() != '' and '/' in select_data_caoption.get('NEWO_L', ''):
            newol1 = add_space_between_text_and_number(
                select_data_caoption.get('NEWO_L', '').split("/")[0])
            newol2 = add_space_between_text_and_number(
                select_data_caoption.get('NEWO_L', '').split("/")[1])
            cats_dict['New_to_Old_Ratio'] = newol1 + "/" + newol2
        elif (select_data_caoption.get('NEWO_D', '')).strip() != '' and '/' in select_data_caoption.get('NEWO_D', ''):
            newod1 = add_space_between_text_and_number(
                select_data_caoption.get('NEWO_D', '').split("/")[0])
            newod2 = add_space_between_text_and_number(
                select_data_caoption.get('NEWO_D', '').split("/")[1])
            cats_dict['New_to_Old_Ratio'] = newod1 + "/" + newod2
    else:
        cats_dict['New_to_Old_Ratio'] = ''
    return row, cats_dict


def amtoutstanding_amtredeem_fun(row, cats_dict, select_data_caoption):

    if row.get(
        'rawcatype',
        ''
    ) in (
        'INTR',
        'PCAL',
        'EXTM',
        'BMET',
        'BIDS',
        'CHAN',
        'CONS',
        'CONV',
        'DFLT',
        'EXOF',
        'PINK',
        'TEND'
    ):
        cats_dict['amtoutstanding'] = ''
        cats_dict['amtredeem'] = ''

    elif row.get('rawcatype', '') == 'PRED':
        # cats_dict['amtoutstanding'] != '0'
        if row.get(
            'Next_Factor',
            ''
        ) != '' and (
            row.get(
                'AmountIssued',
                ''
            )
        ).replace(
            "M",
            "000"
        ) != '':
            row['amtoutstanding'] = str(
                round(
                    float(
                        (row.get(
                            'AmountIssued',
                            ''
                        )).replace(
                            "M",
                            "000"
                        )
                    ) *
                    float(
                        row.get(
                            'Next_Factor',
                            ''
                        ).replace(
                            ',',
                            ''
                        )
                    )
                )
            )

            cats_dict['amtoutstanding'] = base_obj.pre_process.amountissued_format(
                row.get('amtoutstanding', ''))

        if row.get(
            'Next_Factor',
            ''
        ).replace(
            ",",
            ""
        ) != '' and row.get(
            'Previous_Factor',
            ''
        ).replace(
            ",",
            ""
        ) and (
            row.get(
                'AmountIssued',
                ''
            )
        ).replace(
            "M",
            "000"
        ) != '':
            row['amtredeem'] = str(
                (float(
                    row.get(
                        'Previous_Factor',
                        ''
                    ).replace(
                        ",",
                        ""
                    )
                ) -
                    float(
                    row.get(
                        'Next_Factor',
                        ''
                    ).replace(
                        ",",
                        ""
                    )
                )) *
                round(
                    float(
                        (row.get(
                            'AmountIssued',
                            ''
                        )).replace(
                            "M",
                            "000"
                        )
                    )
                )
            )
            cats_dict['amtredeem'] = base_obj.pre_process.amountissued_format(
                row.get('amtredeem', ''))

            # amtredeem_format
    elif row.get('rawcatype', '') in ('MCAL', 'BPUT'):
        cats_dict['amtoutstanding'] = '0'
        if (row.get('AmountIssued', '')).replace("M", "000") != '' and (
            select_data_caoption.get('A_rate', '')
        ).replace(",", '') != '':
            cats_dict['amtredeem'] = ((float((select_data_caoption.get('A_rate', '')).replace(
                ",", ''))) / 100) * int(round(float((row.get('AmountIssued', '')).replace("M", "000"))))
            cats_dict['amtredeem'] = base_obj.pre_process.amountissued_format(
                cats_dict.get('amtredeem', ''))
    elif row.get('rawcatype', '') == 'REDM':
        cats_dict['amtoutstanding'] = '0'
        if (row.get('AmountIssued', '')).replace("M", "000") != '' and (
            select_data_caoption.get('A_rate', '')
        ).replace(",", '') != '':
            cats_dict['amtredeem'] = ((float((select_data_caoption.get('A_rate', '')).replace(
                ",", ''))) / 100) * (float((row.get('AmountIssued', '')).replace("M", "000")))
            cats_dict['amtredeem'] = base_obj.pre_process.amountissued_format(
                cats_dict.get('amtredeem', ''))

    if str(
        row.get(
            'amtoutstanding',
            ''
        )
    ) == '0' or str(
        row.get(
            'amtoutstanding',
            ''
        )
    ) == '0.0':
        cats_dict['amtoutstanding'] = ''

    if str(
        row.get(
            'amtredeem',
            ''
        )
    ) == '0' or str(
        row.get(
            'amtredeem',
            ''
        )
    ) == '0.0':
        cats_dict['amtredeem'] = ''

    row['amtredeem'] = cats_dict['amtredeem']
    row['amtoutstanding'] = cats_dict['amtoutstanding']

    return row, cats_dict


def notes_fun(row, effectivedate, cats_dict):

    if str(row.get('MaturityDate', '')) != '':
        maturitydate = row.get('MaturityDate', '').date().strftime("%d-%b-%Y")
    else:
        maturitydate = ''

    # maturity_val = row.get('MaturityDate', '')

    # if pd.notna(maturity_val):
    #     maturitydate = maturity_val.date().strftime("%d-%b-%Y")
    # else:
    #     maturitydate = ''

    if row.get(
        'rawcatype',
        ''
    ) == 'EXTM' and str(
        row.get(
            'new_maturity_date_EXTM',
            ''
        )
    ).replace(
        "None",
        ""
    ) != '':
        try:
            if datetime.strptime(str(row.get('new_maturity_date_EXTM', '')), "%Y%m%d").date(
            ) != row.get('MaturityDate', '').date() or maturitydate == '':
                new_maturity_date = datetime.strptime(
                    str(row.get('new_maturity_date_EXTM', '')), "%Y%m%d").strftime("%d-%b-%Y")
                row['New_Maturity_Date'] = datetime.strptime(
                    str(row.get('new_maturity_date_EXTM', '')), "%Y%m%d").strftime("%Y-%m-%d")
            else:
                new_maturity_date = ''
                row['Comments_Entry'] = 'Rejected - EXTM - Maturity Date is same for FISIN and Euroclear'
        except:
            new_maturity_date = ''
            row['Comments_Entry'] = 'Rejected - EXTM - Maturity Date is same for FISIN and Euroclear'
    else:
        new_maturity_date = ''

    if row.get('f_Issuecurrency', '').strip() != '':
        issuecurrency = row.get('f_Issuecurrency', '')
    elif row.get('IssueCurrency', '').strip() != '':
        issuecurrency = row.get('IssueCurrency', '')
    else:
        row['Comments_Entry'] = 'Issuecurrency Blank'

    if row.get('rawcatype', '') != 'PCAL':
        if row.get('catype_id', '') == '4':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has called to redeem all of the outstanding {issuecurrency} {
                cats_dict.get(
                    'amtredeem',
                    '')}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'BondType',
                    '')} rate bond due {maturitydate} on {effectivedate}. The outstanding balance will therefore be zero.'''

        elif row.get('catype_id', '') == '25':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced has fully repurchased {issuecurrency} {
                cats_dict.get(
                    'amtredeem',
                    '')}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'BondType',
                    '')} rate bond due {maturitydate} on {effectivedate}. The outstanding balance will therefore be zero.'''

        elif row.get('catype_id', '') == '454':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} announced that it has made the payment of interest relating to its {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '445':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it will make such interest payment due on {effectivedate} will be made as PIK by adding the interest amount to the principal of the bond issue relating to it {issuecurrency}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '2' and cats_dict.get('amtoutstanding', '').strip() != '':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has made amortizing for its {issuecurrency} {
                cats_dict.get(
                    'amtredeem',
                    '')}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} due {maturitydate}. The outstanding balance will therefore be {issuecurrency} {
                cats_dict.get(
                    'amtoutstanding',
                    '')}.'''

        elif row.get('catype_id', '') == '2' and cats_dict.get('amtoutstanding', '').strip() == '':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has made amortizing for its {issuecurrency}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} due {maturitydate} on {effectivedate}.'''

        elif row.get('catype_id', '') == '551':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that the bond has reached its full maturity for {issuecurrency} {
                cats_dict.get(
                    'amtredeem',
                    '')}, {
                row.get(
                    'CouponType',
                    '')} bond due on {maturitydate}.'''

        elif row.get('catype_id', '') == '549':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has held meeting on {effectivedate} for its {issuecurrency} {
                cats_dict.get(
                    'amtoutstanding',
                    '')}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'BondType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '5':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has repurchased any or all of the outstanding {issuecurrency} {
                cats_dict.get(
                    'amtredeem',
                    '')}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'BondType',
                    '')} rate bond due {maturitydate} at the option of the holders on {effectivedate}. The outstanding balance will therefore be zero.'''

        elif row.get('catype_id', '') == '62':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has extended the maturity date for its {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'BondType',
                    '')} rate bond from {maturitydate} to {new_maturity_date}.'''

        elif row.get('catype_id', '') == '34':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it intends to repurchase any or all of the outstanding {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '10':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has converted its {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate} into shares of the company.'''

        elif row.get('catype_id', '') == '12':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has defaulted in payment of interest & principal relating to its {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '378':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has exchanged its {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate} with new security.'''

        elif row.get('catype_id', '') in ('45', '44'):
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has changed the issuer to {
                row.get(
                    'caevent',
                    '')} for its {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '396':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that noteholders have consented to certain modifications to the terms and Conditions of the bond relating to its {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '557':  # TEND CA event notes added on 22/08/24
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that {
                row.get(
                    'By offeror',
                    '')} has intends to repurchase any or all of the outstanding {issuecurrency} {
                (
                    row.get(
                        'AmountIssued',
                        ''))}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '561':  # Wrth CA event notes added on 15/05/25
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has been deemed worthless due to the issuers bankruptcy/liquidation relating to its {issuecurrency}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '455':  # DTCH CA event notes added on 06/06/25
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it agreed to repurchase all or part of its outstanding through a Dutch auction of its  {issuecurrency}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        elif row.get('catype_id', '') == '562':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has been increase in the current principal of a debt instrument without increasing the nominal value relating to its {issuecurrency}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'CouponType',
                    '')} rate bond due {maturitydate}.'''

        # DTCH CA event notes added on 16/04/26
        elif row.get('catype_id', '') == '8' and row.get('Instrument_Redm', '') in ('', None):
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has filed petition for Bankrupcy.'''

        elif row.get('catype_id', '') == '8':  # DTCH CA event notes added on 16/04/26
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} has announced today that bankruptcy has been filed for its {issuecurrency} bond due {maturitydate}.'''

    elif row.get('rawcatype', '') == 'PCAL':
        if row.get(
            'catype_id',
            ''
        ) == '28' and cats_dict.get(
            'amtoutstanding',
            ''
        ).strip() != '':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has partially repurchased of its {issuecurrency} {
                cats_dict.get(
                    'amtredeem',
                    '')}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'BondType',
                    '')} rate bond due {maturitydate} on {effectivedate}. The outstanding balance will therefore be {issuecurrency} {
                cats_dict.get(
                    'amtoutstanding',
                    '')}.'''

        elif row.get('catype_id', '') == '28' and cats_dict.get('amtoutstanding', '').strip() == '':
            row['notes'] = f'''{
                row.get(
                    'EntityName', '')} today announced that it has partially repurchased of its {issuecurrency},{
                row.get(
                    'IssuanceCoupon', '')} {
                row.get(
                    'BondType', '')} rate bond due {maturitydate} on {effectivedate}. '''

        elif row.get('catype_id', '') == '466' and cats_dict.get('amtoutstanding', '').strip() != '':
            row['notes'] = f'''{
                row.get(
                    'EntityName', '')} today announced that it has called to redeem partially of its {issuecurrency} {
                cats_dict.get(
                    'amtredeem', '')},{
                row.get(
                    'IssuanceCoupon', '')} {
                row.get(
                    'BondType', '')} rate bond due {maturitydate} on {effectivedate}. The outstanding balance will therefore be {issuecurrency} {
                cats_dict.get(
                    'amtoutstanding', '')}.'''

        elif row.get('catype_id', '') == '466' and cats_dict.get('amtoutstanding', '').strip() == '':
            row['notes'] = f'''{
                row.get(
                    'EntityName',
                    '')} today announced that it has called to redeem partially of its {issuecurrency}, {
                row.get(
                    'IssuanceCoupon',
                    '')} {
                row.get(
                    'BondType',
                    '')} rate bond due {maturitydate} on {effectivedate}.'''
    return row


def cats_comments_issuecurrency_fun(select_data_caoption, row, cats_dict):

    if row.get('rawcatype', '') == 'PRED':
        cats_dict['Comments'] = 'With pool factor reduction'
    elif row.get('rawcatype', '') == 'PCAL':
        cats_dict['Comments'] = 'Without pool factor reduction'

    if select_data_caoption != '' and select_data_caoption.get(
        'Payment_Currency', ''
    ) != '':
        row['Payment_Currency'] = select_data_caoption.get('Payment_Currency', '')
    else:
        row['Payment_Currency'] = ''

    if row.get('IssueCurrency', '') == '':
        row['IssueCurrency'] = row['Payment_Currency']

    if select_data_caoption.get('CRedemptionprice', '') != '':
        credemption_price = ((((select_data_caoption.get(
            'CRedemptionprice', '')).split("/")[1])).replace(",", "."))
        if credemption_price[-1] == '.':
            cats_dict['CRedemptionprice'] = credemption_price[:-1] + "%"
        else:
            cats_dict['CRedemptionprice'] = "{:.3f}".format(
                float(credemption_price)) + "%"
    elif select_data_caoption.get('CRedemptionprice', '') == '' and select_data_caoption.get('Early_Tender_consideration', '') != '' and row.get('rawcatype', '') in ('MCAL', 'PCAL', 'BPUT', 'REDM', 'PRED'):
        OfferPrice = str((((select_data_caoption.get(
            'Early_Tender_consideration', '')).split("/")[1])).replace(",", "."))[3:]
        if OfferPrice[-1] == '.':
            cats_dict['OfferPrice'] = OfferPrice[:-1]
        else:
            cats_dict['OfferPrice'] = OfferPrice
    else:
        cats_dict['CRedemptionprice'] = ''
        cats_dict['OfferPrice'] = ''

    return row, cats_dict


def catype_based_condition(row, cats_dict, catype_dict, select_data_caoption):

    if row.get('rawcatype', '') == 'TEND':
        if str(row.get('70E_OFFO', '')) != '':
            url = "http://192.168.1.222/api/commons/haircut"
            headers = {'Content-Type': 'application/json'}
            payload = json.dumps({"entitynames": [str(row.get('70E_OFFO', ''))]})
            response = requests.request("POST", url, headers=headers, data=payload)
            feorgs_details = (json.loads(response.text)).get('data', '')

            if str(feorgs_details.get(str(row.get('70E_OFFO', '')))
                   ).replace("None", '') != '':
                row['By Offeror'] = feorgs_details.get(
                    str(row.get('70E_OFFO', ''))).get('entityname')
                row['OFFO_Name'] = str(row.get('70E_OFFO', ''))
                row['fieldname'] = '49'  # '49'By Offeror
                row['OtherValue'] = row['By Offeror']
            else:
                row['Comments_Entry'] = 'Rejected - TEND 70E_OFFO Entityname not in FEORGS'
                row['By Offeror'] = ''
                row['OFFO_Name'] = str(row.get('70E_OFFO', ''))
        else:
            row['By Offeror'] = ''
            row['Comments_Entry'] = 'Rejected - TEND 70E_OFFO is blank'

    if row.get('rawcatype', '') == 'PCAL':
        if (row.get('Calloption', '').strip()).upper() == 'Y':
            row['catype'] = catype_dict.get(row.get('rawcatype', ''))[0]
            row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[1]
        else:
            row['catype'] = catype_dict.get(row.get('rawcatype', ''))[2]
            row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[3]

    elif row.get('rawcatype', '') == 'MCAL':
        if (row.get('Calloption', '').strip()).upper() == 'Y':
            row['catype'] = catype_dict.get(row.get('rawcatype', ''))[0]
            row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[1]
        else:
            row['catype'] = catype_dict.get(row.get('rawcatype', ''))[2]
            row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[3]

    elif row.get('rawcatype', '') == 'CHAN' and str(row.get('NAME_70E', '')).replace("None", "") != '' and str(row.get('CHAN', '')).replace("None", "") != '':
        if (str(row.get('CHAN', '')).replace("None", "")).lower() == 'name':
            row['catype'] = catype_dict.get(row.get('rawcatype', ''))[0]
            row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[1]
        elif (str(row.get('CHAN', '')).replace("None", "")).lower() == 'term':
            row['catype'] = catype_dict.get(row.get('rawcatype', ''))[2]
            row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[3]

        raw_entityname_ferogs, rejection_chan = chan_70_name_populate(row)
        cats_dict['caimpact'] = '8'
        cats_dict['caevent'] = raw_entityname_ferogs
        # row['caimpact'] =   'Target Name' # changed by david on 19/06/25
        row['caimpact'] = '8'
        row['caevent'] = raw_entityname_ferogs
        row['Comments_Entry'] = rejection_chan

    elif str(select_data_caoption.get('CRDB_EXOF', '')).replace("None", '') == 'CRED' and row.get('rawcatype', '') == 'EXOF' and select_data_caoption.get('35B_ISIN', '') != '':
        row['New_Registered_ISIN'] = select_data_caoption.get('35B_ISIN', '')
        row['catype'] = catype_dict.get(row.get('rawcatype', ''))[0]
        row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[1]

    elif row.get('rawcatype', '') != 'CHAN':
        row['catype'] = catype_dict.get(row.get('rawcatype', ''))[0]
        row['catype_id'] = catype_dict.get(row.get('rawcatype', ''), '')[1]

    if str(select_data_caoption.get('Expiration_Date', '')).replace("None", "") != '' and row.get('rawcatype', '') == 'BIDS':
        cats_dict['expirationdate'] = datetime.strptime(str(select_data_caoption.get('Expiration_Date', '')[:8]), "%Y%m%d").strftime("%Y-%m-%d %T")

    if str(row.get('Next_Coupon_Date', '')).strip() != '':
        row['Next_Coupon_Date'] = datetime.strptime(str(row.get('Next_Coupon_Date', '')), "%Y%m%d").strftime("%Y-%m-%d %T")
    else:
        row['Next_Coupon_Date'] = ''

    if str(row.get('RecordDate', '')) != '':
        row['RecordDate'] = datetime.strptime(str(round(int(row.get('RecordDate', '')))), "%Y%m%d").strftime("%Y-%m-%d %T")
    else:
        row['RecordDate'] = ''

    if str(row.get('Coupon_Start_Date_Coupon_End_Date', '')) != '' and len(str(row.get('Coupon_Start_Date_Coupon_End_Date', '')).split("/")) == 2:
        row["Coupon_Start_Date"] = datetime.strptime(str(row.get('Coupon_Start_Date_Coupon_End_Date', '').split("/")[0]), "%Y%m%d").strftime("%Y-%m-%d %T")
        row["Coupon_End_Date"] = datetime.strptime(str(row.get('Coupon_Start_Date_Coupon_End_Date', '').split("/")[1]), "%Y%m%d").strftime("%Y-%m-%d %T")
    else:
        row["Coupon_Start_Date"] = ''
        row["Coupon_End_Date"] = ''

    row['Previous_Factor'] = (str(row.get('Previous_Factor', '')).replace(",", ".")).strip()
    row['Next_Factor'] = (str(row.get('Next_Factor', '')).replace(",", ".")).strip()

    #### Added on 29-4-24 --- CATS-270 (Requested on 26-Apr-2024)
    if row.get('rawcatype', '') in ('BPUT'):
        if select_data_caoption.get('98C_MKDT', '') != '':
            row['Market_Deadline'] = date_format_Change(str(select_data_caoption.get('98C_MKDT', '')[:8]))
        elif select_data_caoption.get('98A_MKDT', '') != '':
            row['Market_Deadline'] = date_format_Change(str(select_data_caoption.get('98A_MKDT', '')[:8]))

    if row.get('rawcatype', '') in ('BIDS', 'CONS', 'CONV', 'EXOF', 'TEND', 'DTCH'):

        if select_data_caoption.get('98C_MKDT', '') != '':
            row['Market_Deadline'] = date_format_Change(str(select_data_caoption.get('98C_MKDT', '')[:8]))
        elif select_data_caoption.get('98A_MKDT', '') != '':
            row['Market_Deadline'] = date_format_Change(str(select_data_caoption.get('98A_MKDT', '')[:8]))

        if select_data_caoption.get('69E_PWAL', '') != '' and '/' in select_data_caoption.get('69E_PWAL', ''):
            row['Period_of_Action_Start_Date'] = date_format_Change(str(select_data_caoption.get('69E_PWAL', '')).split("/")[0])
            row['Period_of_Action_End_Date'] = date_format_Change(str(select_data_caoption.get('69E_PWAL', '')).split("/")[1])
        elif select_data_caoption.get('69C_PWAL', '') != '' and '/' in select_data_caoption.get('69C_PWAL', ''):
            row['Period_of_Action_Start_Date'] = date_format_Change(str(select_data_caoption.get('69C_PWAL', '')).split("/")[0])
            row['Period_of_Action_End_Date'] = date_format_Change(str(select_data_caoption.get('69C_PWAL', '')).split("/")[1])
        elif select_data_caoption.get('69A_PWAL', '') != '' and '/' in select_data_caoption.get('69A_PWAL', ''):
            row['Period_of_Action_Start_Date'] = date_format_Change(str(select_data_caoption.get('69A_PWAL', '')).split("/")[0])
            row['Period_of_Action_End_Date'] = date_format_Change(str(select_data_caoption.get('69A_PWAL', '')).split("/")[1])
        elif select_data_caoption.get('69J_PWAL', '') != '' and '/' in select_data_caoption.get('69J_PWAL', ''):
            row['Period_of_Action_Start_Date'] = date_format_Change(str(select_data_caoption.get('69J_PWAL', '')).split("/")[0])
            row['Period_of_Action_End_Date'] = date_format_Change(str(select_data_caoption.get('69J_PWAL', '')).split("/")[1])

    ####CATS.dbo.CATS_Addfield
    if row.get('rawcatype', '') in ('CONS', 'BIDS', 'EXOF', 'TEND'):
        if row.get('rawcatype', '') == 'BIDS':
            row['fieldname'] = '48'  ### 48 By Issuer
            row['OtherValue'] = row.get('EntityName', '')

        if row.get('rawcatype', '') != 'BIDS':
            if str(select_data_caoption.get('SOFE_1', '')).replace("None", '') != '':
                row['fieldname'] = '27'  ### Consent_Fee
                row['OtherValue'] = select_data_caoption.get("SOFE_1", '')
            elif str(select_data_caoption.get('SOFE_2', '')).replace("None", '') != '':
                row['fieldname'] = '27'  ### Consent_Fee
                row['OtherValue'] = select_data_caoption.get("SOFE_2", '')
        elif row.get('rawcatype', '') != 'BIDS' and row.get('fieldname', '') == '':
            if str(select_data_caoption.get('SOFE_1', '')).replace("None", '') != '':
                row['fieldname'] = '27'  ### Consent_Fee
                row['OtherValue'] = select_data_caoption.get("SOFE_1", '')
            elif str(select_data_caoption.get('SOFE_2', '')).replace("None", '') != '':
                row['fieldname'] = '27'  ### Consent_Fee
                row['OtherValue'] = select_data_caoption.get("SOFE_2", '')
        elif row.get('rawcatype', '') != 'BIDS' and row.get('fieldname', '') != '':
            if str(select_data_caoption.get('SOFE_1', '')).replace("None", '') != '':
                row['fieldname1'] = '27'  ### Consent_Fee
                row['OtherValue1'] = select_data_caoption.get("SOFE_1", '')
            elif str(select_data_caoption.get('SOFE_2', '')).replace("None", '') != '':
                row['fieldname1'] = '27'  ### Consent_Fee
                row['OtherValue1'] = select_data_caoption.get("SOFE_2", '')

        row['Consent_Type_Indicator'] = str(row.get('ConsentTypeIndicator', '')).replace("None", "")
        if str(select_data_caoption.get('ESOF_1', '')).replace("None", '') != '':
            row['Early_Solicitation_Fee_Rate'] = str(select_data_caoption.get('ESOF_1', ''))
            try:
                row['Early_Solicitation_Fee_Rate'] = row['Early_Solicitation_Fee_Rate'].replace(",", "")
            except:
                pass
        elif str(select_data_caoption.get('ESOF_2', '')).replace("None", '') != '':
            row['Early_Solicitation_Fee_Rate'] = str(select_data_caoption.get('ESOF_2', ''))
            try:
                row['Early_Solicitation_Fee_Rate'] = row['Early_Solicitation_Fee_Rate'].replace(",", "")
            except:
                pass
        else:
            row['Early_Solicitation_Fee_Rate'] = ''

    # if str(row.get('New_Coupon_Rate','')).strip() != '':
    #     row['New_Coupon_Rate']  = str((float(str(row.get('New_Coupon_Rate','')).replace(",","."))))
    row['New_Coupon_Rate'] = ''
    if str(row.get("No_of_Days", '')) != '':
        row['No_of_Days'] = str(int(str(row.get("No_of_Days", ''))))

    if row.get('rawcatype', '') == 'DTCH':
        if select_data_caoption.get('98C_RDDT', '') != '':
            year = select_data_caoption.get('98C_RDDT', '')[:4]
            month = select_data_caoption.get('98C_RDDT', '')[4:6]
            date = select_data_caoption.get('98C_RDDT', '')[6:8]
            formatted_value = year + month + date
            row['Response_deadline_date'] = datetime.strptime(formatted_value, "%Y%m%d").strftime("%Y-%m-%d")

    return row, cats_dict


def bulk_comment_update_status(dbstatus, exce):
    if dbstatus == False:
        base_obj.logger.info(''' Process Ended due to Query not update ''')
        sys.exit()
    else:
        base_obj.logger.info(f''' Dbstatus ---- {dbstatus}, {exce}''')
    return


def initial_bulk_rejection():
    # Step 1.1 Rejectiona
    base_obj.logger.info("1.1. Update ---- Comments is Blank")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.[Euroclear_CA_GENRL] SET Comments = '' WHERE Comments LIKE 'CAEvent Captured Exception -%' ''')
    bulk_comment_update_status(dbstatus, exce)

    # Step 1 Rejection
    base_obj.logger.info("1. Update ---- Comments is Blank")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.[Euroclear_CA_GENRL] SET Comments = '' WHERE Comments IS NULL ''')
    bulk_comment_update_status(dbstatus, exce)

    # Step 2 Rejection
    base_obj.logger.info("2. Update ---- Rejected - Blank - ISIN Not Available in FE Database")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' SELECT ISIN INTO #Comments_Update_FERACK54 FROM FERACKSVR.FE1.dbo.FISIN ''')
    bulk_comment_update_status(dbstatus, exce)
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL
            SET comments = ''
            WHERE comments = 'ISIN not available' 
            AND [35B_ISIN] IN (SELECT ISIN FROM #Comments_Update_FERACK54) ''')
    bulk_comment_update_status(dbstatus, exce)

    # Step 3 Rejection
    base_obj.logger.info("3. Update ---- Rejected - Commercial Pappers")
    get_isin_id = '''select f.ISINID, E.id, E.[35B_ISIN] as ISIN  from FERACK72.Euroclear.dbo.[Euroclear_CA_GENRL] E
    JOIN FE1.DBO.FIdentifier I  ON I.ISIN = E.[35B_ISIN]
    LEFT JOIN FE1.dbo.FISIN f  on F.ISINID = I.ISINID
    where E.comments='' '''
    get_data = FERACK.fetchArray_withKey(get_isin_id)
    if get_data:
        for row in get_data:
            check_caid = FERACK.fetchArray_withKey(
                f''' SELECT top 1 caid, c.catype, cagroup,ct.catype[catype_value], effectivedate 
                    FROM CATS.dbo.CATS c 
                    LEFT JOIN cats.dbo.Cats_CAType ct on c.catype = ct.CtypeID 
                    WHERE (c.Catype in (4,315,7,5,474,10,12,551,25,62,458) or CAGroup in (11, 14)) 
                    and isin = '{row.get('ISIN','')}' and isinid = '{row.get('ISINID','')}' 
                    Order by effectivedate desc ''')
            if check_caid:
                if str(check_caid[0].get('catype', '')) in ['474', '458']:  ###Instrument Level Rejection
                    rejection = f'''Rejection due to {check_caid[0].get('catype_value','')}'''
                    catype_rejection_caid = check_caid[0].get('caid', '')
                    FERACK72.query(
                        f''' UPDATE Euroclear.dbo.[Euroclear_CA_GENRL] SET CAID = '{catype_rejection_caid}', Comments = '{rejection}' WHERE id = '{row.get('id','')}' ''')
    # #Step 4 Rejection
    base_obj.logger.info("4. Update ---- Rejected - ISIN Not Available in FE Database")
    dbstatus, exce = FERACK72.query_bulk_update(''' SELECT * INTO #ISIN
            FROM
            (
            SELECT [35B_ISIN] FROM Euroclear.dbo.[Euroclear_CA_GENRL] WHERE Comments = ''
            EXCEPT
            SELECT ISIN FROM FERACKSVR.FE1.dbo.ISIN
            )T


            UPDATE Euroclear.dbo.[Euroclear_CA_GENRL]
            SET Comments = 'ISIN not available'
            WHERE isnull(Comments,'') = '' 
            AND [35B_ISIN] IN
            (
            SELECT [35B_ISIN] FROM #ISIN
            )

        ''')
    bulk_comment_update_status(dbstatus, exce)

    # # Step 5 Rejection
    # base_obj.logger.info("5. Update ---- Rejected - FERACK72_UPDATE_EC_I_ISIN")
    # dbstatus, exce = FERACK.query_bulk_update(''' 
    #         DROP TABLE precats.DBO.FERACK72_UPDATE_EC_I_ISIN
    #      ''')
    # bulk_comment_update_status(dbstatus, exce)

    # #Step 6 Rejection
    # base_obj.logger.info("6. Update ---- Drop - FERACK72_UPDATE_EC_I_ISIN")
    # dbstatus, exce = FERACK.query_bulk_update('''         ;WITH CTE AS      
    #                 (         
    #                     SELECT DISTINCT [35B_ISIN] [ISIN] FROM FERACK72.Euroclear.dbo.Euroclear_CA_GENRL A WITH(NOLOCK) WHERE Comments = 'ISIN not available'      
    #                 )   
    #                 SELECT ISIN INTO precats.DBO.FERACK72_UPDATE_EC_I_ISIN        
    #                 FROM  FE1.DBO.ISIN  WHERE ISIN IN (SELECT ISIN FROM CTE) ''')
    # bulk_comment_update_status(dbstatus, exce)

    #Step 7 Rejection
    base_obj.logger.info("7. Update ---- SELECT - Rejected - ISIN Not Available in FE Database")
    dbstatus, exce = FERACK72.query_bulk_update(''' UPDATE Euroclear.dbo.[Euroclear_CA_GENRL] SET Comments = ''
            WHERE Comments = 'ISIN not available'  AND 
            [35B_ISIN] IN
            (
                SELECT ISIN FROM FERACKSVR.precats.DBO.FERACK54_UPDATE_EC_I_ISIN
            )  ''')
    bulk_comment_update_status(dbstatus, exce)

    #Step 8 Rejection
    base_obj.logger.info("8. Update ---- Rejected - Other Euroclear CAType")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET Comments = 'Rejected - Other Euroclear CAType' WHERE comments = '' and [22F_CAEV] not in ('BPUT','EXTM', 'BMET', 'INTR', 'PRED','MCAL','REDM','PCAL','CHAN', 'CONS','BIDS','CONV','DFLT','EXOF','PINK','TEND','WRTH', 'DTCH','CAPI','BRUP')  ''')
    bulk_comment_update_status(dbstatus, exce)

    #Step 9 Rejection
    base_obj.logger.info("9. Update ---- Rejected - 25D_PROC is not equal to COMP or PREC")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE [Euroclear].[dbo].[Euroclear_CA_GENRL] SET comments = 'Rejected - 25D_PROC is not equal to COMP or PREC'
        WHERE ([25D_PROC] NOT IN ('COMP', 'PREC') OR [25D_PROC] IS NULL) AND isnull(comments,'') = '' ''')
    bulk_comment_update_status(dbstatus, exce)

    #Step 10 Rejection
    base_obj.logger.info("10. Update ---- Rejected - 25D_PROC is not equal to CANC")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET Comments = 'Rejected - 23G column contains CANC' 
        WHERE comments = '' and [22F_CAEV] in ('BPUT','EXTM', 'BMET', 'INTR', 'PRED','MCAL','REDM','PCAL','CONV','DFLT','EXOF','PINK','TEND') and [25D_PROC] IN ('COMP', 'PREC')
        and [23G] = 'CANC' ''')
    bulk_comment_update_status(dbstatus, exce)

    #Step 11 Rejection
    base_obj.logger.info("11. Update ---- Rejected - 25D_PROC is not equal to REPL")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET comments = 'Rejected - 23G column contains REPL' WHERE isnull(comments,'') = '' and [23G] = 'REPL' and [25D_PROC] IN ('COMP', 'PREC') ''')
    bulk_comment_update_status(dbstatus, exce)

    #Step 12 Rejection
    base_obj.logger.info("12. Update ---- Rejected - 23G status is not NEWM")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET Comments = 'Rejected - 23G column contains '+[23G]   
        WHERE comments = '' and [22F_CAEV] in ('CHAN', 'CONS','BIDS','CONV','DFLT','EXOF','PINK','TEND') and [25D_PROC] IN ('COMP', 'PREC')
        and [23G] != 'NEWM'  ''')
    bulk_comment_update_status(dbstatus, exce)

    #Step 13 Rejection
    # base_obj.logger.info("13. Update ----Rejected - INTR Other Bondtype not Fixed")
    # dbstatus, exce = FERACK72.query_bulk_update(''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL  
    #         SET Comments = 'Rejected - INTR Other Bondtype not Fixed'
    #         WHERE  [35B_ISIN] IN 
    #         (
    #         SELECT DISTINCT [35B_ISIN] FROM Euroclear.dbo.Euroclear_CA_GENRL WHERE 
    #         comments  = '' and [22F_CAEV] = 'INTR'and  [23G] <> 'NEWM' and [25D_PROC ]<> 'COMP' 
    #         INTERSECT
    #         SELECT ISIN FROM FERACKSVR.FE1.dbo.FISIN F WITH(NOLOCK) 
    #         WHERE bondtype != 1   
    #         )
    #         AND comments = ''  and [22F_CAEV] = 'INTR'and  [23G] <> 'NEWM' and [25D_PROC ]<> 'COMP' 
    #     ''')
    # bulk_comment_update_status(dbstatus, exce)

    #Step 14 Rejection
    # base_obj.logger.info("14. Update ---- Rejected - INTR Other Bondtype not Fixed")
    # dbstatus, exce = FERACK72.query_bulk_update(''' SELECT * INTO #A FROM
    #         (
    #             SELECT ISIN [ISIN] FROM FERACKSVR.FE1.dbo.FISIN F WITH(NOLOCK) 
    #             WHERE CAST(ISINID as varchar(10)) IN 
    #             (
    #                 SELECT CAST(ISINID as varchar(10)) FROM FERACKSVR.FE1.DBO.FVARIABLE WHERE  CAST(CENDDATE  AS DATE) > CAST(GETDATE() AS DATE) AND SEQNO = 1
    #             )
    #         ) A

    #         UPDATE Euroclear.dbo.Euroclear_CA_GENRL  
    #         SET Comments = ''
    #         WHERE [35B_ISIN] IN 
    #         (
    #             SELECT DISTINCT [35B_ISIN] FROM Euroclear.dbo.Euroclear_CA_GENRL WHERE Comments = 'Rejected - INTR Other Bondtype not Fixed' and [22F_CAEV] = 'INTR'and  [23G] <> 'NEWM' and [25D_PROC ]<> 'COMP' 
    #             INTERSECT
    #             SELECT ISIN FROM #A
    #         )  AND Comments = 'Rejected - INTR Other Bondtype not Fixed' AND [22F_CAEV] = 'INTR'and  [23G] <> 'NEWM' and [25D_PROC ]<> 'COMP' 

    #         DROP TABLE #A

    #         ''')   

    # bulk_comment_update_status(dbstatus, exce)

    #Step 15 Rejection
    base_obj.logger.info("15. Update ---- Rejected - Rejected - For PRED column 92A_NWFC is equal 92A_PRFC")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET Comments = 'Rejected - For PRED column 92A_NWFC is equal 92A_PRFC' WHERE [22F_CAEV] = 'PRED' and [92A_NWFC] = [92A_PRFC] and comments = ''  ''')
    bulk_comment_update_status(dbstatus, exce)

    #Step 16 Rejection
    # dbstatus, exce = FERACK72.query_bulk_update(''' UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET Comments = 'Rejected - 23G column contains CANC' 
    #     WHERE comments != 'Rejected - 23G column contains CANC' and [22F_CAEV] in ('BPUT','EXTM', 'BMET', 'INTR', 'PRED','MCAL','REDM','PCAL','CONV','DFLT','EXOF','PINK','TEND') and [25D_PROC] = 'COMP'
    #     and [23G] = 'CANC' ''')
    # bulk_comment_update_status(dbstatus, exce)
    return


def duplicate():
    query = "select * from [Euroclear].[dbo].[Euroclear_CA_GENRL] where ISNULL(Comments,'')='' "
    records = FERACK54.fetchArray_withKey(query)

    df = pd.DataFrame(records)
    columns_to_ignore = ['FilePath', 'FileCreatedDate', 'DownloadDate',
                         'comments', 'CAID', 'Refid', 'id']
    columns_to_check = df.columns.difference(columns_to_ignore).tolist()
    df['Comments_Dup'] = df.duplicated(subset=columns_to_check, keep='first').apply(
        lambda x: 'Duplicate' if x else 'Unique')
    filtered_df = df[df['Comments_Dup'] == 'Duplicate']

    for idx, data in filtered_df.iterrows():
        record_id = data['id']
        update_query = f"""
        UPDATE [Euroclear].[dbo].[Euroclear_CA_GENRL]
        SET comments = 'Duplicate'
        WHERE id = {record_id} and ISNULL(Comments,'')=''
        """
        print(f"Executing query for id: {record_id}")
        FERACK54.query(update_query)


def duplicate_without_change():
    query = "select * from [Euroclear].[dbo].[Euroclear_CA_GENRL] where ISNULL(Comments,'')='' "
    records = FERACK54.fetchArray_withKey(query)

    df = pd.DataFrame(records)
    columns_to_ignore = ['20C_SEME', '23G', '98C_PREP', '20C_PREV', '25D_PROC', '13A_LINK',
                         '35B_ISIN', 'FilePath', 'FileCreatedDate', 'DownloadDate', 'comments', 'CAID', 'Refid', 'id']
    columns_to_check = df.columns.difference(columns_to_ignore).tolist()
    df['Comments_Dup'] = df.duplicated(subset=columns_to_check, keep='first').apply(
        lambda x: 'Duplicate' if x else 'Unique')
    filtered_df = df[df['Comments_Dup'] == 'Duplicate']

    for idx, data in filtered_df.iterrows():
        record_id = data['id']
        update_query = f"""
        UPDATE [Euroclear].[dbo].[Euroclear_CA_GENRL]
        SET comments = 'Duplicate without change'
        WHERE id = {record_id} and ISNULL(Comments,'')=''
        """
        base_obj.logger.info(f"Executing query for id: {record_id}")
        FERACK54.query(update_query)


def instrumenttype_rejection():
    # intr_rejection
    FERACK72.query(
        f"""UPDATE M SET COMMENTS = '',caid='' FROM Euroclear.dbo.[Euroclear_CA_GENRL] M WHERE INTR_Comments in ('Full_Redemption INTR not Generated','Bond Called INTR not Generated')""")
    # Step 1 Rejection
    base_obj.logger.info("1. Update ---- Comments is Blank")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.[Euroclear_CA_GENRL] SET Comments = '' WHERE Comments IS NULL ''')
    bulk_comment_update_status(dbstatus, exce)

    # Step 1 Rejection
    base_obj.logger.info("1. Update ---- Comments is Blank")
    dbstatus, exce = FERACK72.query_bulk_update(
        ''' UPDATE Euroclear.dbo.[Euroclear_CA_GENRL] SET Comments = '' WHERE Comments = 'Newly_inserted' ''')
    bulk_comment_update_status(dbstatus, exce)

    base_obj.logger.info("instrumenttype_rejection started")

    FERACK72.query(
        f""" UPDATE EUROCLEAR.DBO.Euroclear_CA_GENRL   SET Comments = 'Rejected - Other Instruments Type in 12A_CLAS' 
            WHERE ISNULL(Comments, '') = '' 
            AND [12A_CLAS] IN ('ECLR/CUMWR','ECLR/HYBWR','ECLR/CP','ECLR/CD')   """)

    FERACK.query("""DROP TABLE IF EXISTS #FISIN """)
    FERACK.query("""SELECT ISIN,STATUS INTO #FISIN FROM  FE1.DBO.ISIN with(nolock) """)

    FERACK.query(
        f""" DROP TABLE IF EXISTS #EUROCLEAR """)
    FERACK.query(
        f"""SELECT DISTINCT [35B_ISIN] AS ISIN INTO #EUROCLEAR FROM FERACK72.EUROCLEAR.DBO.EUROCLEAR_CA_GENRL with(nolock) 
            WHERE ISNULL(Comments,'')='' AND ([12A_CLAS] IN ('ECLR/NOTE', 'ECLR/MTN', 'ECLR/BOND', 'ECLR/CONV') 
            or isnull([12A_CLAS],'')='' )   """)

    FERACK.query("""DROP TABLE IF EXISTS #MISSING_ISIN """)
    FERACK.query("""SELECT ISIN INTO #MISSING_ISIN FROM #EUROCLEAR 
                 EXCEPT
                 SELECT ISIN FROM #FISIN""")

    FERACK.query("""DROP TABLE IF EXISTS #CGS """)
    FERACK.query(
        """SELECT  'Rejected due to '+INSTRUMENTTYPE+' in CGS'  [COMMENTS],
        ISIN  into #cgs FROM  FERACK65.CGS.DBO.CGSMETADATA
        WHERE   isnull(INSTRUMENTTYPE,'') not in ('BOND','') AND ISIN IN (SELECT ISIN FROM #MISSING_ISIN)    """)

    records = FERACK.fetchArray_withKey("""SELECT * FROM  #CGS """)

    values_str = ", ".join(
        [f"('{entry.get('ISIN','')}', '{entry.get('COMMENTS','')}')" for entry in records])
    if values_str == '':
        values_str = "('','')"

    FERACK72.query("""DROP TABLE IF EXISTS #Rejection """)
    FERACK72.query(
        f"SELECT * INTO #Rejection FROM (VALUES {values_str}) AS [TAB] (ISIN, COMMENTS)")

    FERACK72.query(f"""UPDATE E SET E.Comments_New = R.COMMENTS ,E.comments ='ISIN not available'
        FROM Euroclear.DBO.Euroclear_CA_GENRL E
        LEFT JOIN #Rejection R ON R.ISIN = E.[35B_ISIN] 
        WHERE R.ISIN IS NOT NULL AND ISNULL(E.Comments,'')=''   """)

    base_obj.logger.info("instrumenttype_rejection in CGS completed")

    FERACK.query(f""" DROP TABLE IF EXISTS #EUROCLEAR """)
    FERACK.query(
        f"""SELECT DISTINCT [35B_ISIN] AS ISIN INTO #EUROCLEAR FROM FERACK72.EUROCLEAR.DBO.EUROCLEAR_CA_GENRL with(nolock) 
            WHERE ISNULL(Comments,'')='' AND ([12A_CLAS] IN ('ECLR/NOTE', 'ECLR/MTN', 'ECLR/BOND', 'ECLR/CONV') 
            or isnull([12A_CLAS],'')='' )  """)

    FERACK.query(f""" DROP TABLE IF EXISTS #MISSING_ISIN """)

    FERACK.query("""SELECT ISIN INTO #MISSING_ISIN FROM #EUROCLEAR 
                 EXCEPT
                 SELECT ISIN FROM #FISIN""")

    FERACK.query("""DROP TABLE IF EXISTS #BBG """)
    FERACK.query(
        f"""SELECT  CASE WHEN ISNULL(MarketSector,'')= '' THEN  'ISIN not available'
        ELSE  'Rejected due to '+MarketSector+' in BBG' END [COMMENTS],
        ISIN  into #BBG FROM  ISIN.DBO.Bloomberg_OpenFIGI
        WHERE   isnull(MarketSector,'') <>'Corp' AND ISIN IN (SELECT ISIN FROM #MISSING_ISIN)    """)

    records = FERACK.fetchArray_withKey("""SELECT * FROM  #BBG """)

    values_str = ", ".join(
        [f"('{entry.get('ISIN','')}', '{entry.get('COMMENTS','')}')" for entry in records])
    if values_str == '':
        values_str = "('','')"

    FERACK72.query(f"""DROP TABLE IF EXISTS #Rejection """)
    FERACK72.query(
        f"""SELECT * INTO #Rejection FROM (VALUES {values_str}) AS [TAB] (ISIN, COMMENTS)""")

    FERACK72.query(f"""UPDATE E SET E.Comments_New = R.COMMENTS ,E.comments ='ISIN not available'
        FROM Euroclear.DBO.Euroclear_CA_GENRL E
        LEFT JOIN #Rejection R ON R.ISIN = E.[35B_ISIN] 
        WHERE R.ISIN IS NOT NULL AND ISNULL(E.Comments,'')=''   """)

    base_obj.logger.info("instrumenttype_rejection in BBG completed")
    FERACK.query(f""" DROP TABLE IF EXISTS #EUROCLEAR """)

    FERACK.query(
        f"""SELECT DISTINCT [35B_ISIN] AS ISIN INTO #EUROCLEAR FROM FERACK72.EUROCLEAR.DBO.EUROCLEAR_CA_GENRL with(nolock) 
            WHERE ISNULL(Comments,'')='' AND ([12A_CLAS] IN ('ECLR/NOTE', 'ECLR/MTN', 'ECLR/BOND', 'ECLR/CONV') 
            or isnull([12A_CLAS],'')='' )  """)

    FERACK.query(f""" DROP TABLE IF EXISTS #MISSING_ISIN """)
    FERACK.query("""SELECT ISIN INTO #MISSING_ISIN FROM #EUROCLEAR 
                 EXCEPT
                 SELECT ISIN FROM #FISIN""")

    records = FERACK.fetchArray_withKey("""SELECT * FROM  #MISSING_ISIN  """)

    values_str = ", ".join(
        [f"('{entry.get('ISIN','')}', 'ISIN not available')" for entry in records])
    if values_str == '':
        values_str = "('','')"

    FERACK72.query(f"""DROP TABLE IF EXISTS #Rejection """)
    FERACK72.query(
        f"""SELECT * INTO #Rejection FROM (VALUES {values_str}) AS [TAB] (ISIN, COMMENTS)""")

    FERACK72.query(f"""UPDATE E SET E.Comments_New = R.COMMENTS ,E.comments ='ISIN not available'
        FROM Euroclear.DBO.Euroclear_CA_GENRL E
        LEFT JOIN #Rejection R ON R.ISIN = E.[35B_ISIN] 
        WHERE R.ISIN IS NOT NULL AND ISNULL(E.Comments,'')=''   """)


def payment_date_seven_days_logic(cats_dict, row):
    # cats_dict['effectivedate']=''
    if cats_dict.get('effectivedate', '') and row.get('catype_id', '') and cats_dict.get('isinid', ''):

        payment_date = cats_dict.get('effectivedate', '').split(" ")[0]
        ca_type = row.get('catype_id', '')
        isin = row.get('ISIN', '')
        cats_table_data = FERACK.fetchArray_withKey(
            f"""select caid, cast(effectivedate as date)[effectivedate] from cats.dbo.cats with(nolock) where isin='{isin}' and catype='{ca_type}' 
                                                        AND CAST(effectivedate AS DATE) 
                                                        BETWEEN DATEADD(DAY, -7, CAST('{payment_date}' AS DATE)) 
                                                        AND DATEADD(DAY, 7, CAST('{payment_date}' AS DATE))
                                                        """)

        if cats_table_data:
            if str(cats_table_data[0].get('effectivedate', '')).split()[0] == payment_date:
                return True, cats_table_data[0].get(
                    'caid', ''), 'CATS Entry Already available'
            else:
                return True, cats_table_data[0].get(
                    'caid', ''), 'Rejected - Payment date falls ±7 days range of the CATS effective date'
        else:
            return False, '', ''
    else:
        return False, '', ''


def main():
    instrumenttype_rejection()
    initial_bulk_rejection()

    # WHERE rn BETWEEN 1 AND 1000
    input_query = f'''
        ;WITH BaseData AS (
            
            SELECT top 15000 *,
                ROW_NUMBER() OVER (ORDER BY A.ID DESC) AS rn
            FROM [Euroclear].[dbo].[Euroclear_CA_GENRL] A WITH (NOLOCK)
            WHERE ISNULL(Comments,'') IN ('', 'requeue') 
            AND [22F_CAEV] IN ('CONS','BIDS','BPUT', 'BMET', 'INTR', 'PRED','MCAL','REDM', 'PCAL','CHAN','CONV','DFLT','EXOF','PINK','TEND','EXTM', 'WRTH', 'DTCH','CAPI','BRUP')
            AND A.ID NOT IN ('201049391')
        ),
        CTE AS (
            SELECT   *
            FROM BaseData WHERE rn BETWEEN 01 AND 1000
            
            
        )
        
        SELECT '19'sourceid,'DP' as Source,'373' as subsourceid,
        CASE WHEN [22F_CAEV] IN ('MCAL','REDM','PDEF','WRTH','BPUT','DRAW','CAPI')
        THEN COALESCE([98C_PREP], [98A_ANOU]) ELSE [98C_PREP] END [AnnounceDate],
        'Euroclear' as subsource,'' as caid, f.ISINID[isinid], f.Issuername[entityname],
        '' as amtoutstanding, '' as amtredeem, e.[FilePath],
        e.[98A_PAYD][effectivedate_PAYD],e.[98C_MEET][effectivedate_MEET_C],e.[98A_MEET][effectivedate_MEET_A],
        ''[effectivedate_VALU], e.[98A_RESU] [effectivedate_CONS], e.[98A_EFFD][effectivedate_EXTM],''[CRedemptionprice_90A_OFFR], 
        '' notes,e.[98A_MATU][new_maturity_date_EXTM],
        ''newssource1, e.[22F_CAEV]rawcatype,'' as [newssource1], e.[35B_ISIN][ISIN],f.ISIN[FISIN_FERACK],
        I.ISIN [ISIN_FERACK],e.SecurityName,e.[70E_ADTX][news2],[70F_ADTX][Narrative_Notes],
        e.[12A_CLAS][instrumenttype], e.[11A_DENO][IssueCurrency],e.[22F_CAEP][CA_Event_Processing_Indicator],
        e.[98A_COUP][Next_Coupon_Date], e.[98A_RDTE][RecordDate],e.[22F_CAMV][MAND_VOLU_Indicator] ,
        e.[69A_INPE][Coupon_Start_Date_Coupon_End_Date], e.[99A_DAAC][No_of_Days], 
        '' as [New_Coupon_Rate],e.[70E_NAME][NAME_70E],e.[22F_CHAN][CHAN],
        e.[92A_PRFC][Previous_Factor], e.[92A_NWFC][Next_Factor],  e.[22F_CONS][ConsentTypeIndicator],
        e.[98C_PREP][announcedate_Redem],e.[25D_PROC][proc_status], e.[23G][proc_sub_status],e.[70E_OFFO],e.[94E_MEET] [Meeting_Place], 
        f.AmountIssued, fe.EntityName, fe.IsCurrent, f.IssueCurrency[f_Issuecurrency],f.Calloption,
        fc.CouponType, f.MaturityDate,f.IssuanceCoupon, e.id ,e.[20C_SEME], e.[20C_CORP],e.[98A_COAP][CourtApprovalDate], 
        e.[36B_MQSO][Maximum_Tender_Amount], e.[36C_QTSO][Minimum_Tender_Amount_C], e.[36B_QTSO][Minimum_Tender_Amount_B], 
        fb.BondType, f.Issuedate, fbb.Bondclassi, f.AmountIssued, e.comments,'NEWM' as [ISO_Function],
        CASE 
            WHEN e.[25D_PROC] IN ('COMP', 'PREC') THEN e.[25D_PROC]
            ELSE NULL
        END AS [CA_status]
        FROM CTE E 
        JOIN FERACKSVR.FE1.DBO.ISIN I with (nolock) ON I.ISIN = E.[35B_ISIN]
        LEFT JOIN FERACKSVR.FE1.dbo.FISIN f with (nolock) on F.ISINID = I.ISINID
        LEFT JOIN FERACKSVR.FE.FE.FEORGS fe with (nolock) on fe.EntityID = f.IssuerName
        LEFT JOIN FERACKSVR.FE1.dbo.FCouponType fc with (nolock) on fc.CTCode = f.CouponType
        LEFT JOIN FERACKSVR.FE1.dbo.FBondType fb with (nolock) on fb.id = f.BondType
        LEFT JOIN FERACKSVR.FE1.dbo.FBondClassification fbb with (nolock) on f.Bondclassi = fbb.id
        WHERE ISNULL(I.ISIN,'') != ''  and ISNULL(e.comments,'') in ('' ,'requeue')
        ORDER by e.id  desc    '''
    records = FERACK72.fetchArray_withKey(input_query)
    df = pd.DataFrame(records).fillna('')
    base_obj.logger.info(f"Total Records to process - {len(records)}")
    count = 0
    for index, row in df.iterrows():
        count += 1
        base_obj.logger.info(
            f"Total records {len(records)}, Processing record {count}, remaining {len(records) - count}, "
            f"with ID {row.get('id', '')} and ISIN {row.get('ISIN', '')}")
        if "." in str(row.get("isinid")):  # to avoid float values in isinid
            row["isinid"] = int(str(row.get("isinid")).split(".")[0])
        if "." in str(row.get("entityname")):  # to avoid float values in entityname
            row["entityname"] = int(str(row.get("entityname")).split(".")[0])
        df4 = pd.DataFrame()
        loop_value = index
        if row['SecurityName'] not in ('', None) and row.get('rawcatype', '') in ('BRUP') and row['instrumenttype'] in ('', None):
            SecName_EntityName = re.search(
                r"//([A-Z\s]+)", row['SecurityName']).group(1).strip() if row['SecurityName'] else ''
            if SecName_EntityName != '':
                Ent_Level_Entname = FERACK.fetchArray_withKey(
                    f''' SELECT IsCurrent, EntityName, ENTITYID FROM FE.FE.FEORGS WHERE ENTITYNAME LIKE '%{SecName_EntityName}%' ''')
                if len(Ent_Level_Entname) >= 1:
                    row['entityname'] = Ent_Level_Entname[0].get('EntityID', '')
                    row['entityname'] = Ent_Level_Entname[0].get('ENTITYID', '')
                    row['IsCurrent'] = 'Y'
                else:
                    FERACK72.query(
                        f" UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET comments = 'Rejected - Entityname not found for BRUP catype'  WHERE id = '{row.get('id')}' ")
                    base_obj.logger.info(
                        f"Entityname not found for BRUP catype - {SecName_EntityName}")
                    continue
            else:
                FERACK72.query(
                    f" UPDATE Euroclear.dbo.Euroclear_CA_GENRL SET comments = 'Rejected - SecurityName format is not proper for BRUP catype'  WHERE id = '{row.get('id')}' ")
                base_obj.logger.info(
                    f"SecurityName format is not proper for BRUP catype - {row['SecurityName']}")
                continue
        # try:
        if row.get('IsCurrent', '') != 'Y':
            current_entity = row.get('entityname', '')
            found_current = False

            while current_entity:
                entitydata = FERACK.fetchArray_withKey(f"""
                    SELECT PARENT.EntityName, PARENT.IsCurrent, PARENT.ENTITYID 
                    FROM FE.FE.FEORGS CHILD WITH (NOLOCK)
                    JOIN FE.FE.FEORGS PARENT WITH (NOLOCK)
                    ON CHILD.SU_ENTITY = PARENT.ENTITYID 
                    WHERE CHILD.ENTITYID = '{current_entity}'
                """)

                if len(entitydata) == 0:
                    FERACK72.query(f"""
                        UPDATE Euroclear.dbo.Euroclear_CA_GENRL 
                        SET comments = 'Rejected - Entity not Found'
                        WHERE id = '{row.get('id')}'
                    """)
                    base_obj.logger.info(
                        f"Entity not found for id {row.get('id', '')} and entityname {row.get('entityname', '')}")
                    break

                row_entity = entitydata[0]
                if row_entity.get('IsCurrent', '') == 'Y':
                    row['entityname'] = row_entity.get('ENTITYID', '')
                    break
                else:
                    current_entity = row_entity.get(
                        'ENTITYID', '') or row_entity.get('EntityName', '')

        catype_dict = {
            'BPUT': ['Full Call', '4', 'Partial Call', '466'],
            'REDM': ['Full Redemption', '551'],
            'PRED': ['Partial Redemption', '2'],
            'PCAL': ['Partial Call', '466', 'Full Call', '4'],
            'INTR': ['Interest Payment', '454'],
            'MCAL': ['Maturity Call', '5', 'Partial Maturity Call', '455'],
            'CONS': ['Consent Solicitation', '396'],
            'EXOF': ['Exchange', '378'],
            'CONV': ['Conversion', '10'],
            'DFLT': ['Default', '12'],
            'PINK': ['Pink Sheet', '562'],
            'EXTM': ['Extension', '62'],
            'BMET': ['Bond Meeting', '549'],
            'BIDS': ['Buyback', '25'],
            'CHAN': ['Name Change', '45'],
            'TEND': ['Tender', '557'],
            'DTCH': ['Dutch Auction', '455'],
            'WRTH': ['Worthless', '561'],
            'CAPI': ['Bankruptcy', '8'],
            'BRUP': ['Bankruptcy', '8'],
        }

        if row.get('rawcatype', '') == '' and row.get('raw_22f', '') in ['PINK', '']:
            pass  # Commented from Euroclear_CA_GENRL

        caid = ''
        selected_instrument_list = [
            row.get('isinid', '')]
        if row.get('isinid', '') != '':
            if row.get('f_Issuecurrency', '') == 'USD':
                selected_instrument_list = [row.get('isinid', '')]
            else:
                instrument_isin = FERACK.fetchArray_withKey(
                    f''' SELECT CAST(ISINID AS VARCHAR(30))[ISINID] FROM FE1.dbo.FIdentifier WHERE ISIN = '{row.get('ISIN', '')}' ''')
                if instrument_isin:
                    selected_instrument_list = [
                        str(each_isin.get('ISINID', '')) for each_isin in instrument_isin]

            for instrument_loop in selected_instrument_list:
                # logic to get caid
                if row.get('rawcatype', '') in ('PRED', 'PCAL'):
                    if str(row.get('Next_Factor', '')).replace(
                            'None', '') != '' and str(row.get('AmountIssued', '')).replace('None', '') != '':
                        caid = generate_caid_auto.generate_caid(
                            row.get('isinid', ''))
                elif row.get('rawcatype', '') == 'BPUT':
                    caid = generate_caid_auto.generate_caid(
                        row.get('isinid', ''))
                else:
                    cats_data = FERACK.fetchArray_withKey(
                        f'''SELECT top 1 caid, catype,effectivedate from cats.dbo.cats where isinid = '{instrument_loop}' and isin = '{row.get('ISIN', '')}' and catype != '396' ORDER BY effectivedate DESC''')
                    if cats_data:
                        caid = cats_data[0].get('caid', '')
                    else:
                        caid = generate_caid_auto.generate_caid(
                            row.get('isinid', ''))
        cats_dict = {}
        cats_dict = row.to_dict()
        row, cats_dict = meeting_place_fun(row, cats_dict)
        row, cats_dict = announcedate_fun(row, cats_dict)
        row, cats_dict, effectivedate = effectivedate_fun(
            row, cats_dict, '')
        row = notes_fun(row, effectivedate, cats_dict)
        row, cats_dict = additional_column_fun(
            row, cats_dict, '')

        row = periodic_coupon_rate_fun('', row)
        row, cats_dict = cats_comments_issuecurrency_fun(
            '', row, cats_dict)
        row, cats_dict = catype_based_condition(
            row, cats_dict, catype_dict, '')
        row, cats_dict = amtoutstanding_amtredeem_fun(
            row, cats_dict, '')


if __name__ == '__main__':
    main()