from gensim.utils import simple_preprocess
from itertools import chain, islice
from datasets import load_dataset
from pathlib import Path
import regex as re

DEACCENT_MAP = {'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
                'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u'}


class Corpora:
    def __init__(self, min_token_len, max_token_len, min_sentence_len):
        self.corpora = []
        self.min_token_len = min_token_len
        self.max_token_len = max_token_len
        self.min_sentence_len = min_sentence_len

    def add_corpus(self, name, source, fraction, repeats):
        if source == 'remote':
            repeats = 1
        for _ in range(repeats):
            self.corpora.append(Corpus(name, source, fraction,
                                       self.min_token_len, self.max_token_len, self.min_sentence_len))

    def get_size(self):
        for corpus in self.corpora:
            print(f'{corpus.name}: {corpus.size // (1024 * 1024)}MB, {corpus.num_sentences} sentences')

    def __iter__(self):
        for sentence in chain.from_iterable(corpus.get_texts() for corpus in self.corpora):
            yield list(sentence['text'])


class Corpus:
    def __init__(self, name, source, fraction, min_token_len, max_token_len, min_sentence_len):
        self.name = name
        self.fraction = fraction
        self.is_remote = source == 'remote'
        self.size = 0
        self.num_sentences = 0
        self.corpus = self.load_corpus(min_token_len, max_token_len, min_sentence_len)

    def load_corpus(self, min_token_len, max_token_len, min_sentence_len):
        corpus = []
        if self.is_remote:
            corpus = self.load_hg_dataset(self.name, min_token_len, max_token_len, min_sentence_len)
        else:
            self.load_local_corpus(Path(self.name), corpus, min_token_len, max_token_len)
        return corpus

    def get_texts(self):
        if self.is_remote and 0 < self.fraction < 1.0:
            return islice(self.corpus, self.num_sentences)
        else:
            return self.corpus

    def load_local_corpus(self, data_path, corpus, min_token_len, max_token_len):
        if data_path.exists():
            files = [f for f in data_path.iterdir()]
            for file in files:
                if file.is_file():
                    with file.open('r') as f:
                        sentences = [{'text': preprocess_str({'text': sentence}, min_token_len, max_token_len)['text']}
                                     for sentence in f.read().split('.')]
                        self.size += sum(len(sentence['text']) for sentence in sentences)
                        self.num_sentences += len(sentences)
                        corpus.extend(sentences)
                elif file.is_dir():
                    self.load_local_corpus(file, corpus, min_token_len, max_token_len)

    def load_hg_dataset(self, name, min_token_len, max_token_len, min_sentence_len):
        corpus = load_dataset('large_spanish_corpus', name=name, split='train', streaming=True)
        corpus = corpus.map(lambda row: preprocess_str(row, min_token_len, max_token_len))
        corpus = corpus.filter(lambda row: len(row['text']) > min_sentence_len)
        self.size = int(corpus.info.splits['train'].num_bytes * self.fraction)
        self.num_sentences = int(corpus.info.splits['train'].num_examples * self.fraction)
        return corpus


def preprocess_str(string, min_token_len, max_token_len):
    deaccent_map = str.maketrans(DEACCENT_MAP)
    string['text'] = re.sub(r'^(?![A-Za-zÁ-Úá-ú]+$).*', '', string['text'])
    string['text'] = string['text'].translate(deaccent_map)
    string['text'] = simple_preprocess(string['text'], min_len=min_token_len, max_len=max_token_len)
    return string
