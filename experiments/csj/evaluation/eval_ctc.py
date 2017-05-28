#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Define evaluation method for CTC network (CSJ corpus)."""

import os
import re
import numpy as np
import Levenshtein
from tqdm import tqdm

# from plot import probs
from utils.labels.character import num2char
from utils.labels.phone import num2phone
from utils.data.sparsetensor import list2sparsetensor, sparsetensor2list
from utils.exception_func import exception
# from utils.util import mkdir


@exception
def do_eval_per(session, per_op, network, dataset,
                eval_batch_size=None, rate=1.0, is_progressbar=False):
    """Evaluate trained model by Phone Error Rate.
    Args:
        session: session of training model
        per_op: operation for computing phone error rate
        network: network to evaluate
        dataset: `Dataset' class
        eval_batch_size: batch size on evaluation
        rate: A float value. Rate of evaluation data to use
        is_progressbar: if True, evaluate during training, else during restoring
    Returns:
        per_global: phone error rate
    """
    if eval_batch_size is None:
        batch_size = network.batch_size
    else:
        batch_size = eval_batch_size

    num_examples = dataset.data_num * rate
    iteration = int(num_examples / batch_size)
    if (num_examples / batch_size) != int(num_examples / batch_size):
        iteration += 1
    per_global = 0

    # setting for progressbar
    iterator = tqdm(range(iteration)) if is_progressbar else range(iteration)

    for step in iterator:
        # create feed dictionary for next mini batch
        inputs, labels, seq_len, _ = dataset.next_batch(batch_size=batch_size)
        indices, values, dense_shape = list2sparsetensor(labels)

        feed_dict = {
            network.inputs_pl: inputs,
            network.label_indices_pl: indices,
            network.label_values_pl: values,
            network.label_shape_pl: dense_shape,
            network.seq_len_pl: seq_len,
            network.keep_prob_input_pl: 1.0,
            network.keep_prob_hidden_pl: 1.0
        }

        batch_size_each = len(labels)

        per_local = session.run(per_op, feed_dict=feed_dict)
        per_global += per_local * batch_size_each

    per_global /= dataset.data_num
    print('  Phone Error Rate: %f' % per_global)

    return per_global


@exception
def do_eval_cer(session, decode_op, network, dataset,
                eval_batch_size=None, rate=1.0, is_progressbar=False):
    """Evaluate trained model by Character Error Rate.
    Args:
        session: session of training model
        decode_op: operation for decoding
        network: network to evaluate
        dataset: Dataset class
        eval_batch_size: batch size on evaluation
        rate: rate of evaluation data to use
        is_progressbar: if True, visualize progressbar
    Return:
        cer_mean: mean character error rate
    """
    if eval_batch_size is None:
        batch_size = network.batch_size
    else:
        batch_size = eval_batch_size

    num_examples = dataset.data_num * rate
    iteration = int(num_examples / batch_size)
    if (num_examples / batch_size) != int(num_examples / batch_size):
        iteration += 1
    cer_sum = 0

    # setting for progressbar
    iterator = tqdm(range(iteration)) if is_progressbar else range(iteration)

    map_file_path = '../evaluation/mapping_files/ctc/char2num.txt'
    for step in iterator:
        # create feed dictionary for next mini batch
        inputs, labels, seq_len, _ = dataset.next_batch(batch_size=batch_size)
        indices, values, dense_shape = list2sparsetensor(labels)

        feed_dict = {
            network.inputs_pl: inputs,
            network.label_indices_pl: indices,
            network.label_values_pl: values,
            network.label_shape_pl: dense_shape,
            network.seq_len_pl: seq_len,
            network.keep_prob_input_pl: 1.0,
            network.keep_prob_hidden_pl: 1.0
        }

        batch_size_each = len(labels)
        labels_st = session.run(decode_op, feed_dict=feed_dict)
        labels_pred = sparsetensor2list(labels_st, batch_size_each)
        for i_batch in range(batch_size_each):

            # convert from list to string
            str_pred = num2char(labels_pred[i_batch], map_file_path)
            str_true = num2char(labels[i_batch], map_file_path)
            # print(str_pred)
            # print(str_true)

            # compute edit distance
            cer_each = Levenshtein.distance(
                str_pred, str_true) / len(list(str_true))
            cer_sum += cer_each
            # print(cer_each)

    cer_mean = cer_sum / dataset.data_num
    print('  Character Error Rate: %f' % cer_mean)
    return cer_mean


def decode_test(session, decode_op, network, dataset, label_type,
                eval_batch_size=None, rate=1.0):
    """Visualize label outputs.
    Args:
        session: session of training model
        decode_op: operation for decoding
        network: network to evaluate
        dataset: Dataset class
        label_type: phone or character
        eval_batch_size: batch size on evaluation
        rate: rate of evaluation data to use
    """
    batch_size = 1
    num_examples = dataset.data_num * rate
    iteration = int(num_examples / batch_size)
    if (num_examples / batch_size) != int(num_examples / batch_size):
        iteration += 1

    map_file_path_phone = '../evaluation/mapping_files/ctc/phone2num.txt'
    map_file_path_char = '../evaluation/mapping_files/ctc/char2num.txt'
    for step in range(iteration):
        # create feed dictionary for next mini batch
        inputs, labels, seq_len, input_names = dataset.next_batch(
            batch_size=batch_size)
        indices, values, dense_shape = list2sparsetensor(labels)

        feed_dict = {
            network.inputs_pl: inputs,
            network.label_indices_pl: indices,
            network.label_values_pl: values,
            network.label_shape_pl: dense_shape,
            network.seq_len_pl: seq_len,
            network.keep_prob_input_pl: 1.0,
            network.keep_prob_hidden_pl: 1.0
        }

        # visualize
        batch_size_each = len(labels)
        labels_st = session.run(decode_op, feed_dict=feed_dict)
        labels_pred = sparsetensor2list(labels_st, batch_size_each)
        for i_batch in range(batch_size_each):
            if label_type == 'character':
                print('-----wav: %s-----' % input_names[i_batch])
                print('Pred: ', end="")
                print(
                    ''.join(num2char(labels_pred[i_batch], map_file_path_char)))
                print('True: ', end="")
                print(''.join(num2char(labels[i_batch], map_file_path_char)))
            elif label_type == 'phone':
                print('-----wav: %s-----' % input_names[i_batch])
                print('Pred: ', end="")
                print(
                    ' '.join(num2phone(labels_pred[i_batch], map_file_path_phone)))
                print('True: ', end="")
                print(
                    ' '.join(num2phone(labels[i_batch], map_file_path_phone)))