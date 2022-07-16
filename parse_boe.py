import re
import PyPDF2
from glob import glob
import pandas as pd
import json
import itertools


def pdf_to_text(input_file, output_file):

    with open(input_file, "rb") as file:
        pdfReader = PyPDF2.PdfFileReader(file)

        transcript = ""

        for i in range(pdfReader.numPages):

            # create a page object
            pageObj = pdfReader.getPage(i)

            # extracting text from page
            text = pageObj.extractText()

            transcript += f"{text}\n"

    with open(output_file, "w") as of:
        of.write(transcript)

    return transcript


def multiple_invoice(transcript):
    boe_num = re.sub(
        "CBEXIV Number\s?:\n\s",
        "",
        re.sub("\n\sDETAILS OF AUTHORIZED COURIER", "", re.search(r"CBEXIV Number\s?:\n\s.+(\n\s.+)?\n\sDETAILS OF AUTHORIZED COURIER", transcript).group()),
    )

    hawb_num = (
        re.search(r"House\s+Airway\s+Bill\s+\(HAWB\)\s+Number :\n\s\d+", transcript)
        .group()
        .split()[-1]
        .strip()
    )

    consignor_name = re.sub(
        "SUPPLIER DETAILS\n\sName\s?:\n\s",
        "",
        re.sub("\n\sAddress", "", re.search(r"SUPPLIER DETAILS\n\sName\s?:\n\s.+(\n\s.+)?\n\sAddress", transcript).group()),
    )

    total_freight = re.sub("Total Freight\s?:\n\s", "", re.search(r"Total Freight\s?:\n\s(\d*\.)?\d+", transcript).group())
    total_insurance = re.sub("Total Insurance\s?:\n\s", "", re.search(r"Total Insurance\s?:\n\s(\d*\.)?\d+", transcript).group())

    rate_of_exchange = re.sub(
        "Rate Of Exchange\s?:\n\s",
        "",
        re.search(r"Rate Of Exchange\s?:\n\s(\d*\.)?\d+", transcript).group(),
    )


    num_of_invoices = int(
        re.search(r"Number of Invoices\s?:\n\s\d+", transcript)
        .group()
        .split()[-1]
        .strip()
    )

    invoices = re.split(r"Details Of Invoice - \d+", transcript)[1:]

    invoice_list = []

    for i in range(num_of_invoices):
        invoice = invoices[i]

        invoice_num = re.sub(r"Invoice Number\s?:\n\s", "", re.search(r"Invoice Number\s?:\n\s.+", invoice).group())
        invoice_value = re.sub(r"Invoice Value\s?:\n\s", "", re.search(r"Invoice Value\s?:\n\s\d+", invoice).group())
        
        description = re.finditer(
            r"Item Description\s?:.*?General Description",
            invoice, re.DOTALL
        )

        assessable_values = re.finditer(
            r"Assessable Value\s?:\n\s(\d*\.)?\d+", invoice
        )

        unit_of_measure = re.finditer(r"Unit of Measure\s?:\n\s.+", invoice)
        currency_of_unit_price = re.finditer(
            r"Currency for Unit Price\s?:\n\s.+", invoice
        )
        unit_price = re.finditer(r"Unit Price :\n\s(\d*\.)?\d+", invoice)
        quantity = re.finditer(r"Quantity :\n\s(\d*\.)?\d+", invoice)
        ctsh = re.finditer(r"CTSH :\n\s\d+", invoice)
        bcd_amt = re.finditer(r"BCD(\n\s\d+){4,4}", invoice)
        sw_srchrg_amt = re.finditer(r"SW Srchrg(\n\s\d+){4,4}", invoice)
        igst_rate = re.finditer(r"IGST\n\s\d+", invoice)
        igst_amt = re.finditer(r"IGST(\n\s\d+){4,4}", invoice)


        items = itertools.zip_longest(
            description,
            unit_of_measure,
            unit_price,
            currency_of_unit_price,
            assessable_values,
            quantity,
            ctsh,
            bcd_amt,
            sw_srchrg_amt,
            igst_rate,
            igst_amt,
            fillvalue="NA"
        )
        items_list = []

        for d, um, up, cup, assv, q, c, b, s, ir, ia in items:
            item_obj = {}

            item_obj["description"] = re.sub(
                "(Page \d+ of \d+)",
                "",
                re.sub(r"(Name of Manufacturer)?(General Description)?", "", 
                    d.group()
                    .replace("\n ", "")
                    .split(":")[-1]
                )
            )

            item_obj["unit_of_measure"] = re.sub("Unit of Measure\s?:\n\s", "", um.group())

            item_obj["currency_of_unit_price"] = re.sub(
                "Currency [for]{2,3} Unit Price\s?:\n\s", "", cup.group()
            )


            item_obj["assessable_value"] = re.sub(
                "Assessable Value\s?:\n\s", "", assv.group()
            )
            item_obj["unit_price"] = re.sub("Unit Price\s?:\n\s", "", up.group())

            item_obj["quantity"] = re.sub("Quantity\s?:\n\s", "", q.group())


            item_obj["ctsh"] = c.group().split()[-1].strip()

            item_obj["bcd_amt"] = b.group().split()[-1].strip()
            item_obj["sw_srchrg_amt"] = s.group().split()[-1].strip()
            item_obj["igst_rate"] = ir.group().split()[-1].strip()
            item_obj["igst_amt"] = ia.group().split()[-1].strip()

            items_list.append(item_obj)

        invoice_details = {}
        invoice_details['inv_num'] = invoice_num
        invoice_details['inv_val'] = invoice_value
        invoice_details['items'] = items_list

        invoice_list.append(invoice_details)
        

    
    return {
        "bill_type": "1",
        "boe_number": boe_num,
        "hawb_number": hawb_num,
        "consignor_name": consignor_name,
        "rate_of_exchange": rate_of_exchange,
        "total_freight": total_freight,
        "total_insurance": total_insurance,
        "invoice_list": invoice_list
    }


def single_invoice(transcript):

    invoice_list = []

    boe_num = (
        re.search(r"CBE-XIII Number\n\s.+(\n\s.+)?\n\sName of the", transcript)
        .group()
        .replace("\n ", "")
        .replace("CBE-XIII Number", "")
        .replace("Name of the", "")
    )

    hawb_num = (
        re.search(r"HAWB Number\s?:\n\s\d+", transcript).group().split()[-1].strip()
    )
    ########### MAKE CHANGE TO ALSO INCLUDE MULTIPLE LINES
    consignor_name = re.sub(
        "Name of Consignor\s?:\n\s",
        "",
        re.search(r"Name of Consignor\s?:\n\s.+", transcript).group(),
    ).replace("\n ", "")

    rate_of_exchange = re.sub(
        "Rate of Exchange\s?:\n\s",
        "",
        re.search(r"Rate of Exchange\s?:\n\s(\d*\.)?\d+", transcript).group(),
    )

    assessable_values = re.finditer(
        r"Assessable Value\s?:\n\s(\d*\.)?\d+", transcript
    )
    invoice_values = re.finditer(r"Invoice Value\s?:\n\s(\d*\.)?\d+", transcript)


    total_invoice_value = re.sub(
        "Invoice Value\s?:\n\s", "", next(invoice_values).group()
    )
    total_assessable_value = re.sub(
        "Assessable Value\s?:\n\s", "", next(assessable_values).group()
    )

    invoice_num = re.search(r"Invoice Number :\n\s.+", transcript).group().split()[-1].strip()

    description = re.finditer(
        r"Description of Goods\s?:\n\s.+(\n\s.+)?(\n\sPage \d+ of \d+\n)?\n\sName of Manufacturer",
        transcript,
    )
    unit_of_measure = re.finditer(r"Unit of Measure\s?:\n\s.+", transcript)
    quantity = re.finditer(r"Quantity :\n\s(\d*\.)?\d+", transcript)
    unit_price = re.finditer(r"Unit Price :\n\s(\d*\.)?\d+", transcript)
    currency_of_unit_price = re.finditer(
        r"Currency of Unit Price\s?:\n\s.+", transcript
    )
    freight = re.finditer(r"Freight\s?:\n\s(\d*\.)?\d+", transcript)
    ctsh = re.finditer(r"CTSH :\n\s\d+", transcript)
    bcd_amt = re.finditer(r"BCD(\n\s\d+){4,4}", transcript)
    sw_srchrg_amt = re.finditer(r"SW Srchrg(\n\s\d+){4,4}", transcript)
    igst_rate = re.finditer(r"IGST\n\s\d+", transcript)
    igst_amt = re.finditer(r"IGST(\n\s\d+){4,4}", transcript)

    items = itertools.zip_longest(
        description,
        unit_of_measure,
        unit_price,
        currency_of_unit_price,
        assessable_values,
        invoice_values,
        freight,
        quantity,
        ctsh,
        bcd_amt,
        sw_srchrg_amt,
        igst_rate,
        igst_amt,
        fillvalue="NA"
    )

    items_list = []

    for d, um, up, cup, assv, invv, f, q, c, b, s, ir, ia in items:
        item_obj = {}

        item_obj["description"] = re.sub(
            "(Page \d+ of \d+)",
            "",
            re.sub(r"(Name of Manufacturer)?(General Description)?", "", 
                d.group()
                .replace("\n ", "")
                .split(":")[-1]
            )
        )

        item_obj["unit_of_measure"] = re.sub("Unit of Measure\s?:\n\s", "", um.group())

        item_obj["currency_of_unit_price"] = re.sub(
            "Currency [for]{2,3} Unit Price\s?:\n\s", "", cup.group()
        )
        
        item_obj["freight"] = re.sub("Freight\s?:\n\s", "", f.group())
        item_obj["final_value"] = re.sub("Invoice Value\s?:\n\s", "", invv.group())

        item_obj["assessable_value"] = re.sub(
            "Assessable Value\s?:\n\s", "", assv.group()
        )
        item_obj["unit_price"] = re.sub("Unit Price\s?:\n\s", "", up.group())

        item_obj["quantity"] = re.sub("Quantity\s?:\n\s", "", q.group())


        item_obj["ctsh"] = c.group().split()[-1].strip()

        item_obj["bcd_amt"] = b.group().split()[-1].strip()
        item_obj["sw_srchrg_amt"] = s.group().split()[-1].strip()
        item_obj["igst_rate"] = ir.group().split()[-1].strip()
        item_obj["igst_amt"] = ia.group().split()[-1].strip()

        items_list.append(item_obj)

    invoice_details = {}
    invoice_details['inv_num'] = invoice_num
    invoice_details['inv_val'] = total_invoice_value
    invoice_details['items'] = items_list

    invoice_list.append(invoice_details)

    return {
        "bill_type": "2",
        "boe_number": boe_num,
        "hawb_number": hawb_num,
        "consignor_name": consignor_name,
        "rate_of_exchange": rate_of_exchange,
        "total_invoice_value": total_invoice_value,
        "total_assessable_value": total_assessable_value,
        "invoice_list": invoice_list
    }


def parse(transcript):

    bill_type = int(
        input(
            """
        |---------------------------------------------------------------------------------------------------|

                                            Choose type of BOE
                                                Multiple Invoice     ---> 1
                                                Single Invoice       ---> 2
        |---------------------------------------------------------------------------------------------------|

        Enter your choice: """,
        )
    )

    if bill_type == 1:
        json_obj = multiple_invoice(transcript) 
    elif bill_type == 2:
        json_obj = single_invoice(transcript) 
    else:
        print("Invalid choice. Please restart and select from the given options.")


    with open("new_boe_data.txt", "w+") as f:
        # this would place the entire output in one line
        json.dump(json_obj, f)

    with open("new_boe_data_debug.txt", "w+") as f:
        # format as json document
        json.dump(json_obj, f, indent=4)        


def main(input_file, output_file):
    transcript = pdf_to_text(input_file, output_file)
    parse(transcript)
    input('Completed successfully. Press "Enter" to exit...')

if __name__ == "__main__":
    input_pdf = glob("*.pdf")
    output_txt = "pdf_transcript.txt"

    if len(input_pdf) > 1:
        print("More than one pdf file found in the current folder. Keep only one and try again.")

    elif len(input_pdf) < 1:
        print("No BOE pdf file found.")

    else:
        main(input_pdf[0], output_txt)

