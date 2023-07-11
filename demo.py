import os
from argparse import ArgumentParser
import time
import torch
from mmcv.image import imread
import json
from mmdet.apis import init_detector
from mmocr.apis.inference import model_inference
from mmocr.datasets import build_dataset  # noqa: F401
from mmocr.models import build_detector  # noqa: F401

import sys
import glob
import time
import pickle
import numpy as np
from tqdm import tqdm

from table_recognition.table_inference import Structure_Recognition
import re
import copy


def deal_isolate_span(thead_part):
    """
    Deal with isolate span cases in this function.
    It causes by wrong prediction in structure recognition model.
    eg. predict <td rowspan="2"></td> to <td></td> rowspan="2"></b></td>.
    :param thead_part:
    :return:
    """
    # 1. find out isolate span tokens.
    isolate_pattern = "<td></td> rowspan=\"(\d)+\" colspan=\"(\d)+\"></b></td>|" \
                      "<td></td> colspan=\"(\d)+\" rowspan=\"(\d)+\"></b></td>|" \
                      "<td></td> rowspan=\"(\d)+\"></b></td>|" \
                      "<td></td> colspan=\"(\d)+\"></b></td>"
    isolate_iter = re.finditer(isolate_pattern, thead_part)
    isolate_list = [i.group() for i in isolate_iter]

    # 2. find out span number, by step 1 results.
    span_pattern = " rowspan=\"(\d)+\" colspan=\"(\d)+\"|" \
                   " colspan=\"(\d)+\" rowspan=\"(\d)+\"|" \
                   " rowspan=\"(\d)+\"|" \
                   " colspan=\"(\d)+\""
    corrected_list = []
    for isolate_item in isolate_list:
        span_part = re.search(span_pattern, isolate_item)
        spanStr_in_isolateItem = span_part.group()
        # 3. merge the span number into the span token format string.
        if spanStr_in_isolateItem is not None:
            corrected_item = '<td{}></td>'.format(spanStr_in_isolateItem)
            corrected_list.append(corrected_item)
        else:
            corrected_list.append(None)

    # 4. replace original isolated token.
    for corrected_item, isolate_item in zip(corrected_list,isolate_list):
        if corrected_item is not None:
            thead_part = thead_part.replace(isolate_item, corrected_item)
        else:
            pass
    return thead_part


def deal_duplicate_bb(thead_part):
    """
    Deal duplicate <b> or </b> after replace.
    Keep one <b></b> in a <td></td> token.
    :param thead_part:
    :return:
    """
    # 1. find out <td></td> in <thead></thead>.
    td_pattern = "<td rowspan=\"(\d)+\" colspan=\"(\d)+\">(.+?)</td>|" \
                 "<td colspan=\"(\d)+\" rowspan=\"(\d)+\">(.+?)</td>|" \
                 "<td rowspan=\"(\d)+\">(.+?)</td>|" \
                 "<td colspan=\"(\d)+\">(.+?)</td>|" \
                 "<td>(.*?)</td>"
    td_iter = re.finditer(td_pattern, thead_part)
    td_list = [t.group() for t in td_iter]

    # 2. is multiply <b></b> in <td></td> or not?
    new_td_list = []
    for td_item in td_list:
        if td_item.count('<b>') > 1 or td_item.count('</b>') > 1:
            # multiply <b></b> in <td></td> case.
            # 1. remove all <b></b>
            td_item = td_item.replace('<b>','').replace('</b>','')
            # 2. replace <tb> -> <tb><b>, </tb> -> </b></tb>.
            td_item = td_item.replace('<td>', '<td><b>').replace('</td>', '</b></td>')
            new_td_list.append(td_item)
        else:
            new_td_list.append(td_item)

    # 3. replace original thead part.
    for td_item, new_td_item in zip(td_list, new_td_list):
        thead_part = thead_part.replace(td_item, new_td_item)
    return thead_part


def deal_bb(result_token, tag_='thead'):
    """
    In our opinion, <b></b> always occurs in <thead></thead> text's context.
    This function will find out all tokens in <thead></thead> and insert <b></b> by manual.
    :param result_token:
    :param tag_:
    :return:
    """
    # find out <thead></thead> parts.
    thead_pattern = '<' + tag_ + '>(.*?)</' + tag_ + '>'
    if re.search(thead_pattern, result_token) is None:
        return result_token
    thead_part = re.search(thead_pattern, result_token).group()
    origin_thead_part = copy.deepcopy(thead_part)

    # check "rowspan" or "colspan" occur in <thead></thead> parts or not .
    span_pattern = "<td rowspan=\"(\d)+\" colspan=\"(\d)+\">|<td colspan=\"(\d)+\" rowspan=\"(\d)+\">|<td rowspan=\"(\d)+\">|<td colspan=\"(\d)+\">"
    span_iter = re.finditer(span_pattern, thead_part)
    span_list = [s.group() for s in span_iter]
    has_span_in_head = True if len(span_list) > 0 else False

    if not has_span_in_head:
        # <thead></thead> not include "rowspan" or "colspan" branch 1.
        # 1. replace <td> to <td><b>, and </td> to </b></td>
        # 2. it is possible to predict text include <b> or </b> by Text-line recognition,
        #    so we replace <b><b> to <b>, and </b></b> to </b>
        thead_part = thead_part.replace('<td>', '<td><b>')\
            .replace('</td>', '</b></td>')\
            .replace('<b><b>', '<b>')\
            .replace('</b></b>', '</b>')
    else:
        # <thead></thead> include "rowspan" or "colspan" branch 2.
        # Firstly, we deal rowspan or colspan cases.
        # 1. replace > to ><b>
        # 2. replace </td> to </b></td>
        # 3. it is possible to predict text include <b> or </b> by Text-line recognition,
        #    so we replace <b><b> to <b>, and </b><b> to </b>

        # Secondly, deal ordinary cases like branch 1

        # replace ">" to "<b>"
        replaced_span_list = []
        for sp in span_list:
            replaced_span_list.append(sp.replace('>', '><b>'))
        for sp, rsp in zip(span_list, replaced_span_list):
            thead_part = thead_part.replace(sp, rsp)

        # replace "</td>" to "</b></td>"
        thead_part = thead_part.replace('</td>', '</b></td>')

        # remove duplicated <b> by re.sub
        mb_pattern = "(<b>)+"
        single_b_string = "<b>"
        thead_part = re.sub(mb_pattern, single_b_string, thead_part)

        mgb_pattern = "(</b>)+"
        single_gb_string = "</b>"
        thead_part = re.sub(mgb_pattern, single_gb_string, thead_part)

        # ordinary cases like branch 1
        thead_part = thead_part.replace('<td>', '<td><b>').replace('<b><b>', '<b>')


    # convert <tb><b></b></tb> back to <tb></tb>, empty cell has no <b></b>.
    # but space cell(<tb> </tb>)  is suitable for <td><b> </b></td>
    thead_part = thead_part.replace('<td><b></b></td>', '<td></td>')
    # deal with duplicated <b></b>
    thead_part = deal_duplicate_bb(thead_part)
    # deal with isolate span tokens, which causes by wrong predict by structure prediction.
    # eg.PMC5994107_011_00.png
    thead_part = deal_isolate_span(thead_part)
    # replace original result with new thead part.
    result_token = result_token.replace(origin_thead_part, thead_part)
    return result_token


def merge_span_token(master_token_list):
    """
    Merge the span style token (row span or col span).
    :param master_token_list:
    :return:
    """
    new_master_token_list = []
    pointer = 0
    if master_token_list[-1] != '</tbody>':
        master_token_list.append('</tbody>')
    while pointer < len(master_token_list) and master_token_list[pointer] != '</tbody>':
        try:
            if master_token_list[pointer] == '<td':
                if (pointer + 5) <= len(master_token_list) and (master_token_list[pointer+2].startswith(' colspan=') or
                                                                master_token_list[pointer+2].startswith(' rowspan=')):
                    """
                    example:
                    pattern <td rowspan="2" colspan="3">
                    '<td' + 'rowspan=" "' + 'colspan=" "' + '>' + '</td>'
                    """
                    # tmp = master_token_list[pointer] + master_token_list[pointer+1] + \
                    #       master_token_list[pointer+2] + master_token_list[pointer+3] + master_token_list[pointer+4]
                    tmp = ''.join(master_token_list[pointer:pointer+4+1])
                    pointer += 5
                    new_master_token_list.append(tmp)

                elif (pointer + 4) <= len(master_token_list) and \
                        (master_token_list[pointer+1].startswith(' colspan=') or
                         master_token_list[pointer+1].startswith(' rowspan=')):
                    """
                    example:
                    pattern <td colspan="3">
                    '<td' + 'colspan=" "' + '>' + '</td>'
                    """
                    # tmp = master_token_list[pointer] + master_token_list[pointer+1] + master_token_list[pointer+2] + \
                    #       master_token_list[pointer+3]
                    tmp = ''.join(master_token_list[pointer:pointer+3+1])
                    pointer += 4
                    new_master_token_list.append(tmp)

                else:
                    new_master_token_list.append(master_token_list[pointer])
                    pointer += 1
            else:
                new_master_token_list.append(master_token_list[pointer])
                pointer += 1
        except:
            print("Break in merge...")
            break
    new_master_token_list.append('</tbody>')

    return new_master_token_list


def deal_eb_token(master_token):
    """
    post process with <eb></eb>, <eb1></eb1>, ...
    emptyBboxTokenDict = {
        "[]": '<eb></eb>',
        "[' ']": '<eb1></eb1>',
        "['<b>', ' ', '</b>']": '<eb2></eb2>',
        "['\\u2028', '\\u2028']": '<eb3></eb3>',
        "['<sup>', ' ', '</sup>']": '<eb4></eb4>',
        "['<b>', '</b>']": '<eb5></eb5>',
        "['<i>', ' ', '</i>']": '<eb6></eb6>',
        "['<b>', '<i>', '</i>', '</b>']": '<eb7></eb7>',
        "['<b>', '<i>', ' ', '</i>', '</b>']": '<eb8></eb8>',
        "['<i>', '</i>']": '<eb9></eb9>',
        "['<b>', ' ', '\\u2028', ' ', '\\u2028', ' ', '</b>']": '<eb10></eb10>',
    }
    :param master_token:
    :return:
    """
    master_token = master_token.replace('<eb></eb>', '<td></td>')
    master_token = master_token.replace('<eb1></eb1>', '<td> </td>')
    master_token = master_token.replace('<eb2></eb2>', '<td><b> </b></td>')
    master_token = master_token.replace('<eb3></eb3>', '<td>\u2028\u2028</td>')
    master_token = master_token.replace('<eb4></eb4>', '<td><sup> </sup></td>')
    master_token = master_token.replace('<eb5></eb5>', '<td><b></b></td>')
    master_token = master_token.replace('<eb6></eb6>', '<td><i> </i></td>')
    master_token = master_token.replace('<eb7></eb7>', '<td><b><i></i></b></td>')
    master_token = master_token.replace('<eb8></eb8>', '<td><b><i> </i></b></td>')
    master_token = master_token.replace('<eb9></eb9>', '<td><i></i></td>')
    master_token = master_token.replace('<eb10></eb10>', '<td><b> \u2028 \u2028 </b></td>')
    return master_token


def insert_text_to_token(master_token_list, cell_content_list):
    """
    Insert OCR text result to structure token.
    :param master_token_list:
    :param cell_content_list:
    :return:
    """
    master_token_list = merge_span_token(master_token_list)
    merged_result_list = []
    text_count = 0
    for master_token in master_token_list:
        if master_token.startswith('<td'):
            if text_count > len(cell_content_list)-1:
                text_count += 1
                continue
            else:
                master_token = master_token.replace('><', '>{}<'.format(cell_content_list[text_count]))
                text_count += 1
        master_token = deal_eb_token(master_token)
        merged_result_list.append(master_token)

    return ''.join(merged_result_list)


def text_to_list(master_token):
    # insert virtual master token
    master_token_list = master_token.split(',')

    if master_token_list[-1] == '<td></td>':
        master_token_list.append('</tr>')
        master_token_list.append('</tbody>')
    elif master_token_list[-1] != '</tbody>':
        master_token_list.append('</tbody>')

    if master_token_list[-2] != '</tr>':
        master_token_list.insert(-1, '</tr>')

    return master_token_list


def visual_pred_bboxes(bboxes, filename, dir_path, dir_img):
    """
    visual after normalized bbox in results.
    :param results:
    :return:
    """
    import cv2
    import numpy as np

    img = cv2.imread(dir_img + filename)
    save_path = dir_path + '/visual_pred_bboxes/{}_pred_bbox.png'. \
        format(filename.split('.')[0])

    # print(save_path)

    # x,y,w,h to x,y,x,y
    new_bboxes = np.empty_like(bboxes)
    new_bboxes[..., 0] = bboxes[..., 0] - bboxes[..., 2] / 2
    new_bboxes[..., 1] = bboxes[..., 1] - bboxes[..., 3] / 2
    new_bboxes[..., 2] = bboxes[..., 0] + bboxes[..., 2] / 2
    new_bboxes[..., 3] = bboxes[..., 1] + bboxes[..., 3] / 2
    # draw
    for new_bbox in new_bboxes:
        img = cv2.rectangle(img, (int(new_bbox[0]), int(new_bbox[1])),
                            (int(new_bbox[2]), int(new_bbox[3])), (255, 0, 0), thickness=1)
    cv2.imwrite(save_path, img)

start_time = time.time()
def htmlPostProcess(text):
    text = '<html><body><table>' + text + '</table></body></html>'
    return text


#######################################
# version4 this one need minimal changes while accepting the images 
import os
import sys
import time
import json
from argparse import ArgumentParser
# from table_recognition.demo.structure_recognition import Structure_Recognition
# from table_recognition.demo.utils import text_to_list, insert_text_to_token, deal_bb
# import torch

start_time = time.time()

if len(sys.argv) > 1:
    img_path = sys.argv[1]
    img_name = os.path.basename(img_path)
else:
    # Default values if no command-line argument is provided
    img_path = './table_recognition/demo/7.png'
    img_name = '7.png'

if __name__ == '__main__':

        parser = ArgumentParser()
        parser.add_argument('--tablemaster_config', type=str,
                            default='./configs/textrecog/master/table_master_ResnetExtract_Ranger_0705_cell150_batch4.py',
                            help='tablemaster config file')
        parser.add_argument('--tablemaster_checkpoint', type=str,
                            default='/home/ravi/Desktop/MTL_tabnet/PubTabNet/epoch_19.pth',
                            help='tablemaster checkpoint file')
        parser.add_argument('--out_dir',
                            type=str, default='/home/ravi/Desktop/MTL_tabnet/PubTabNet/', help='Dir to save results')
        args = parser.parse_args()

        print("Time taken for Argument Parsing: %s seconds" % (time.time() - start_time))

        import sys
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        import subprocess
        print("started compiling image.py")
        subprocess.call(['python3', '/home/ravi/Desktop/Layout Parser/image.py'])
        print("completed running image.py subprogram")
        cropped_folder = '/home/ravi/Desktop/Layout Parser/cropped'
        cropped_images = os.listdir(cropped_folder)

        # Read mapping from output.json file generated by image.py subprocess
        with open('/home/ravi/Desktop/Layout Parser/cropped/output.json', 'r') as json_in:
            mapping_list = json.load(json_in)

        for mapping_dict in mapping_list:
            page_id = mapping_dict['page']
            table_id = mapping_dict['tableNumber']
            img_name = f'page_{page_id}table_{table_id}.jpg'
            img_path = os.path.join(cropped_folder, img_name)

            # table structure predict
            tablemaster_inference = Structure_Recognition(args.tablemaster_config, args.tablemaster_checkpoint)
            tablemaster_result, tablemaster_result_dict = tablemaster_inference.predict_single_file(img_path)
            torch.cuda.empty_cache()
            del tablemaster_inference
            print("Time taken for Table Structure Prediction: %s seconds" % (time.time() - start_time))
            pred_text = tablemaster_result_dict[img_name]['text']
            pred_cells = tablemaster_result_dict[img_name]['cell']
            pred_html = insert_text_to_token(text_to_list(pred_text), pred_cells)
            pred_html = deal_bb(pred_html, 'thead')
            pred_html = deal_bb(pred_html, 'tbody')

            # Add <table> at the start and </table> at the end of pred_html
            pred_html = '<table>' + pred_html + '</table>'

            # visualize bboxes
            # visual_pred_bboxes(tablemaster_result_dict[img_name]['bbox'], img_name, './table_recognition/demo/', './table_recognition/demo/')

            # with open(os.path.join('./table_recognition/demo/visual_pred_bboxes/', img_name.replace('.png', '.txt')), 'w') as f:
            #     f.write(pred_html + '\n')
            print("Time taken for Visualization: %s seconds" % (time.time() - start_time))

            print(pred_html)

            # Add HTML representation of table to mapping_dict
            mapping_dict['htmlTable'] = pred_html

        # Save updated mapping to output2.json file
        with open("output2.json", 'w') as json_out:
            json.dump(mapping_list, json_out, indent=4)

        print("Mapping updated successfully in output2.json.")