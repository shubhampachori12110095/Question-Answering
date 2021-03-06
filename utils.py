# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
#import joblib
import random
import os
import numpy

def read_word_vectors(filename, embed_dim=300, labled=False, splitter=' '):
    import sys
    import gzip
    import math
    word_vecs = {}
    if filename.endswith('.gz'): file_object = gzip.open(filename, 'r')
    else: file_object = open(filename, 'r')

    for line_num, line in enumerate(file_object):
        line = line.decode('utf-8').strip()
        splited = line.split(splitter)
        word = (' '.join(splited[:-embed_dim])).strip().encode('utf-8')

        if labled:
            word = word.split(':')[1]

        word_vecs[word] = numpy.array(map(float, splited[-embed_dim:]))
        # for index, vec_val in enumerate(splited[-embed_dim:]):
        #     word_vecs[word][index] = float(vec_val)
        # word_vecs[word] /= math.sqrt((word_vecs[word]**2).sum() + 1e-6) #normalizer

    sys.stderr.write("Vectors read from: "+filename+" \n")
    return word_vecs

def init_embedding_table(filename='embeddings/vocab_embeddings.txt', embed_dim=300, vocab_file='squad_rare/vocab.txt'):
    import theano
    vocab = ['<DUMMY>', '<EOA>', '@placeholder', '<UNK>'] + [ w.strip().split()[0] for w in open(vocab_file) ]
    reverse_vocab = {w: i for i, w in enumerate(vocab)}
    word_vecs = read_word_vectors(filename,embed_dim)
    embeddings = numpy.ndarray(shape=(len(vocab), embed_dim),dtype=theano.config.floatX)
    count = 0
    for k,v in word_vecs.iteritems():
        if k.upper() in ['<DUMMY>', '<EOA>', '@placeholder', '<UNK>']:
            k = k.upper()
        # print (count)
        # print (reverse_vocab[k])
        count += 1
        embeddings[reverse_vocab[k],:] = v

    return embeddings

def write_vocab_embeddings(input_file, vocab_file='squad_rare/vocab.txt',embed_path='embeddings', embed_dim=300):
    word_vecs = read_word_vectors(input_file, embed_dim=embed_dim, splitter=' ')
    vocab = ['<DUMMY>', '<EOA>', '@placeholder', '<UNK>'] + [ w.strip().split()[0] for w in open(vocab_file) ]
    vocab_embeddings = open(os.path.join(embed_path,'vocab_embeddings.txt'),'w')

    unk_words = 0
    sigma = 0.2
    mu = 0

    for i,word in enumerate(vocab):
        if word in word_vecs:
            embed_string = ' '.join(map(str,word_vecs[word].tolist()))
        else: #sigma * np.random.randn(...) + mu
            rand_embed = sigma * numpy.random.randn(embed_dim) + mu
            embed_string = ' '.join(map(str,rand_embed.tolist()))
            unk_words += 1
        vocab_embeddings.write(word+' '+embed_string+'\n')

    vocab_embeddings.close()
    print("unk_words: %d"%unk_words)
    print("file written")

def generate_squad_vocab(path, vocabulary_size=30000):
    import json
    import itertools
    # from operator import itemgetter
    from nltk.probability import FreqDist
    d = json.load(open(path))
    tokenized_sentences = []
    for reading in d['data']:
        for paragraph in reading['paragraphs']:
            sentence = paragraph['context'].lower()
            tokenized_sentences.append(nltk.tokenize.word_tokenize(sentence))
            for question in paragraph['qas']:
                sentence = question['question'].lower()     #TODO later check whether to add answer as well or not
                tokenized_sentences.append(nltk.tokenize.word_tokenize(sentence))

    word_freq = nltk.FreqDist(itertools.chain(*tokenized_sentences))
    print('total uniq words:', len(word_freq))
    # sorted_freq = sorted(dict(word_freq).items(), key=itemgetter(1))[::-1]
    full_vocab = word_freq.most_common(len(word_freq))
    vocab = open('vocab_full.txt','w')
    for w in full_vocab:
        vocab.write(w[0]+'\t'+str(w[1])+'\n')
    vocab.close()
    shorted_vocab = word_freq.most_common(vocabulary_size-1)
    vocab = open('vocab.txt','w')
    for w in shorted_vocab:
        vocab.write(w[0]+'\t'+str(w[1])+'\n')
    vocab.close()

def add_rare_to_vocab(vocab_path='squad/vocab.txt', rare_count=100):
    with open(vocab_path,'r+') as vocab:
        content = vocab.read()
        vocab.seek(0,0)
        for i in range(rare_count):
            vocab.write('@rare'+str(i)+' 0\n')
        vocab.write(content)

def add_rare(ctx, q, a_list, vocab):

    rare_dict = {}
    rares = vocab[4:104]
    ctx = ctx.split(' ')
    q = q.split(' ')
    a = [a.split(' ') for a in a_list]

    iterable = [ctx,q] + a

    for i, words in enumerate(iterable):

        for index, word in enumerate(iterable[i]):
            if not word in vocab or any(ord(char) not in range(128) for char in word):
                if i >= 2:
                    if word in rare_dict:
                        iterable[i][index] = rare_dict[word]
                        # print (word +' to '+ rare_dict[word])
                    else:
                        rare_can = random.choice(rares)
                        rares.remove(rare_can)
                        rare_dict[word] = rare_can
                        iterable[i][index] = rare_dict[word]
                        print (rare_dict[word])

                else:
                    if word in rare_dict:
                        if i >= 2:
                        iterable[i][index] = rare_dict[word]
                        # print (word +' to '+ rare_dict[word])
                    else:
                        if len(rares) == 0:
                            return (False,'','','')
                        rare_can = random.choice(rares)
                        rares.remove(rare_can)
                        rare_dict[word] = rare_can
                        iterable[i][index] = rare_dict[word]

    return (True, ' '.join(iterable[0]), ' '.join(iterable[1]), [' '.join(a) for a in iterable[2:]])

def add_rare_to_squad(data_path='squad/dev-v1.0_tokenized.json',new_path='squad_rare_test', vocab_file='squad_rare/vocab.txt'):
    import json
    import itertools
    import os
    d = json.load(open(data_path))
    file_name = data_path.split('/')[1]
    tokenized_sentences = []
    vocab = ['<DUMMY>', '<EOA>', '@placeholder', '<UNK>'] + [ w.strip().split()[0] for w in open(vocab_file) ]

    print(vocab[4:104])
    for reading in d['data']:
        for paragraph in reading['paragraphs']:
            for question in paragraph['qas']:
                answers = [answer['text'].strip().lower() for answer in question['answers']]
                status,paragraph['context'],question['question'],answers = add_rare(paragraph['context'], question['question'], answers, vocab)
                for i,answer in enumerate(question['answers']):
                    question['answers'][i]['text'] = answers[i]
                    # print(question['answers'])

    with open(os.path.join(new_path, file_name),'w') as outfile:
        json.dump(d, outfile)

def add_rare_to_cnn_document(i, file_name, data_path, new_path, vocab):
    global bad_ctxs_count
    if i % 1000 == 0:
        print('added rare to: %d'%i)
    lines = [l.decode("UTF-8").rstrip('\n') for l in open(os.path.join(data_path,file_name))]
    status, ctx, q, a = add_rare(lines[2].lower(), lines[4].lower(), lines[6].lower(), vocab)
    if not status:
        #bad_ctxs_count += 1
        print('bad_ctxs_count')#: %d'%bad_ctxs_count)
    else:
        new_file = open(os.path.join(new_path,file_name),'w')
        new_file.write('\n'.join(lines[0:2])+'\n')
        new_file.write(ctx+'\n\n')
        new_file.write(q+'\n\n')
        new_file.write(a+'\n\n')
        new_file.close()


def add_rare_to_cnn(data_path='deepmind-qa/cnn/questions/training',new_path='deepmind-qa/cnn_rare/questions/training', vocab_file='squad_rare/vocab.txt'):
    import itertools
    vocab = ['<DUMMY>', '<EOA>', '@placeholder', '<UNK>'] + [ w.strip().split()[0] for w in open(vocab_file) ]

    l = [f for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f))]
    print("number of files: "+str(len(l)))
    joblib.Parallel(n_jobs=-1)(joblib.delayed(add_rare_to_cnn_document)(i,file_name,data_path,new_path,vocab) for i,file_name in enumerate(l))


def unanonymise_cnn(path='cnn_questions', new_path='cnn_new_questions'):
    import os
    import re
    l = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    print("number of files: "+str(len(l)))
    for i,file_name in enumerate(l):
        if i % 1000 == 0:
            print('unanonymised: %d'%i)
        lines = [l.rstrip('\n') for l in open(os.path.join(path,file_name))]
        entity_dict = dict([(s.split(':')[0],s.split(':')[1]) for s in lines[8:]])
        new_lines = []
        for line in lines:
            # print (line)
            for k,v in entity_dict.items():
                line = re.sub(r"%s\b" % k , v, line)
            # print (line)
            new_lines.append(line)
        new_file = open(os.path.join(new_path,file_name),'w')
        new_file.write( '\n'.join(new_lines) )
        new_file.close()

def compute_length_coverage(train_path='new_dev-v1.0_tokenized.json'):
    import json
    import itertools
    # import matplotlib.pyplot as plt
    untokenized = json.load(open("squad/dev-v1.0.json"))
    d = json.load(open(train_path))
    rared = json.load(open('squad_rare/dev-v1.0_tokenized.json'))
    lengths = []
    count = 0
    total = 0
    for i,reading in enumerate(d['data']):
        for j,paragraph in enumerate(reading['paragraphs']):
            context = paragraph['context']
            for k,question in enumerate(paragraph['qas']):
                answer = question['answers'][0]['text']
                q = question['question']
                total += 1
                if answer in context:
                    pass
                else:
                    count += 1
                    print ("-------")
                    print ("C: "+context)
                    print ("C: "+untokenized['data'][i]['paragraphs'][j]['context'])
                    print('--')
                    print ('Q: '+q)
                    print('--')
                    print ("A: "+answer)
                lengths.append(len(question['answers'][0]['text'].split(' ')))
    print (count)
    print(total)

def compute_average_margin(path, example_count=1836975):
    data = open(path,'r')
    data = data.readlines()
    count = 0.0
    sum_of_margins = 0.0
    for i in range(example_count):
        count += 1.0
        sum_of_margins = (float(data[i*11 + 4].strip()) - float(data[i*11 + 8].strip()))


    print ("count: ", count)
    print ("sum_of_margins: ", sum_of_margins)
    print ("average margin: ", sum_of_margins/count)

def tokenize_data(path, new_path):
    import json
    import nltk
    import itertools
    # from operator import itemgetter
    from nltk.probability import FreqDist
    d = json.load(open(path))

    tokenized_sentences = []
    for reading in d['data']:
        for paragraph in reading['paragraphs']:
            context_text = paragraph['context'].lower()


            for question in paragraph['qas']:
                question['question'] = ' '.join(nltk.tokenize.word_tokenize(question['question'].lower()))
                for i,answer in enumerate(question['answers']):
                    answer_start_index = context_text.find(question['answers'][i]['text'].strip().lower())
                    if answer_start_index == -1:
                        answer_start_index = question['answers'][i]['answer_start']
                    answer_length = len(question['answers'][i]['text'].strip())
                    answer_text = context_text[answer_start_index:answer_start_index + answer_length].strip()

                    context_before_answer = context_text[:answer_start_index].lower()
                    context_after_answer = context_text[answer_start_index+answer_length:].lower()
                    tokenized_answer = nltk.tokenize.word_tokenize(answer_text)
                    question['answers'][i]['text'] = ' '.join(tokenized_answer)
                    # context_list = nltk.tokenize.word_tokenize(context_befor_answer) + tokenized_answer +  nltk.tokenize.word_tokenize(context_after_answer)
                    tokenized_context = ' '.join(nltk.tokenize.word_tokenize(context_before_answer)) + \
                                       ' '+' '.join(tokenized_answer)+' '+\
                                       ' '.join(nltk.tokenize.word_tokenize(context_after_answer))

                    paragraph['context'] = tokenized_context


    with open(new_path,'w') as outfile:
        json.dump(d, outfile)

def main():

    tokenize_data('squad/train-v1.0.json', 'squad/train-v1.0_tokenized.json' )


if __name__ == '__main__':
    main()
