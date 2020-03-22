# import pandas
import nltk
import numpy
from pandas import DataFrame, Series, read_csv, read_pickle
from re import sub
from nltk.stem import wordnet
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk import pos_tag
from sklearn.metrics import pairwise_distances
from nltk import word_tokenize
from nltk.corpus import stopwords

from clean_master_data import DataCleaner

class LaurAI:
    """
    A chatbot that reads in data and given context will produce a response 
    based on the trained data
    """

    def __init__(self, data, use_cleaned_data=True):
        self.data = data[["comment", "response"]]
        self.data_cleaner = DataCleaner()
        self.cleaned_data = DataFrame(columns=["Question", "Answer"])
        # use data if provided
        if use_cleaned_data:
            self.cleaned_data = read_pickle("data/master_data_cleaned.pkl")
            if len(self.cleaned_data) != len(self.data):
                # if the data does not match, retrain
                print("New data found. Please wait as this data is processed")
                self.cleaned_data = self.data_cleaner.clean_data(self.data)
                # to improve speed, save to master cleaned
                self.cleaned_data.to_pickle("data/master_data_cleaned.pkl")

        self.finalText = DataFrame(columns=["Lemmas"])
        self.c = CountVectorizer()
        self.bag = None

    def clean_line(self, line):
        ''' 
        Clean the line
        This line makes all lowercase, and removes anything that isn't a number
        '''
        return sub(r'[^a-z ]', '', str(line).lower())

    def tokenize_and_tag_line(self, line):
        ''' Tokenizes the words then tags the tokenized words '''
        return pos_tag(word_tokenize(line), None)

    def create_lemma_line(self, input_line):
        ''' We create the lemmatizer object '''
        lemma = wordnet.WordNetLemmatizer()
        # This is an array for the current line that we will append values to
        line = []
        for token, ttype in input_line:
            checks = ["a", "v", "r", "n"]
            if(ttype[0].lower() not in checks):
                ttype = "n"
            line.append(lemma.lemmatize(token, ttype[0].lower()))
        return {"Lemmas": " ".join(line)}

    def create_lemma(self):
        ''' Creates lemmas for the cleaned data (lemma is the lower )'''
        lemmas = []
        for j in self.cleaned_data.iterrows():
            lemmas.append(self.create_lemma_line(j[1][0]))
        self.finalText = self.finalText.append(lemmas)

    def create_bag_of_words(self):
        '''
        create a bag of words and save in a dataframe with the same indicies as
        the master data
        '''
        self.bag = DataFrame(self.c.fit_transform(self.finalText["Lemmas"]).toarray(),
                             columns=self.c.get_feature_names(), index=self.data.index)

    def askQuestion(self, question):
        '''
        @param question: a string context given by the user
        output a string response to context
        ---
        Compute most similar context to the input using semisupervised learning
        and return approproate response to the determined most similar context
        '''
        
        # Removes all "stop words"
        valid_words = []
        for i in question.split():
            if i not in stopwords.words("english"):
                valid_words.append(i)

        # Clean the data and get tokenized and tagged data
        valid_sentence = self.tokenize_and_tag_line(self.clean_line(" ".join(valid_words)))
        lemma_line = self.create_lemma_line(valid_sentence)

        try:
            index = self.determine_most_similar_context(lemma_line)
            # print(index)
            # print(self.data.loc[index, "comment"])

            # respond with response to most similar context
            answer = self.data.loc[index, "response"]
            return answer
        except KeyError:
            # an unknown word was passed
            return "I am miss pwesident uwu"

    def determine_most_similar_context(self, lemma_line):
        '''
        @param lemma_line: a dictionary of words from the input
        ----
        returne index of datapoint with most similar context to one given
        '''
        # create dataframe of one row initialized to zeros
        # this will represent the lemma
        valid_sentence = DataFrame(0, columns=self.bag.columns, index=[0])

        # set column of 1's for words in lemma line
        for i in lemma_line["Lemmas"].split(' '):
            if i in valid_sentence.columns:
                # if the column exists, laur.ai recognizes the word
                # if laur.ai recognizes the word, it will on it
                # otherwise, do not
                valid_sentence.loc[:, i] = 1

        # find cosine similarity
        cosine = 1 - pairwise_distances(self.bag, valid_sentence, metric="cosine")
        # prepare data to be used in series with data's index
        cosine = Series(cosine.reshape(1,-1)[0], index=self.data.index)

        # determine index of element with highest similarity
        # the answer is the response at this index
        # if it does not find any datapoints similar then it recognizes nothing
        # in the input and the index returned is 0

        return cosine.idxmax()


print("Please wait as Laur.AI loads")

data_master = read_csv("data/master_data.csv")
laurBot = LaurAI(data_master)

# First we need to clean the data, so it is all lower case and without special characters or numbers
# We can then tokenize the data, which means splitting it up into words instead of a phrase. We also
# need to know the type of word

# Then we lematize which means to convert the word into it's base form
laurBot.create_lemma()

# Now we can start to create the bag of words
laurBot.create_bag_of_words()


# Then we can ask a question
# laurBot.askQuestion("What is a funny movie we can watch?")
print("Ask me anything :)")
print("Control C or Type \"Bye\" to quit")
while(True):
    context = input("> ")
    if context.lower() == "bye":
        print("bye :))")
        break
    else:
        response = laurBot.askQuestion(context)
        print(response)
