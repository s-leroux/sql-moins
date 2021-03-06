import unittest

import sqlm.parser as parser

class TokenizerTestCase(unittest.TestCase):
    def test_unquote(self):
        """Test unquoted representation of tokens.
        """
        tc = (  # token                     # unquoted representation
                ("Abc"                      , "Abc"),
                ("'abc'"                    , "abc"),
                ("\"abc\""                  , "abc"),
                ("\"ab''c\""                , "ab''c"),
                ("'ab''c'"                  , "ab'c"),
                ("'ab''''c'"                , "ab''c"),
                ("''"                       , ""),
                ("''''"                     , "'"),
                ("\"\""                     , ""),
                ("\"''\""                   , "''"),
            )
        for test, expected in tc:
            self.assertEqual(parser._unquote(test), expected, test)

    def test_parse_good(self):
        tc = (  # string                    # tokens
                ("ED fn [FOR evt]",         ["ED","fn",["FOR","evt"]]),
                ("ED fn [[FOR] evt]",       ["ED","fn",[["FOR"],"evt"]]),
            )
        for test, expected in tc:
            tokens = parser.tokenize(test)
            self.assertSequenceEqual(parser._parse(tokens), expected, test)
        
    def test_parse_bad(self):
        tc = (  # string   
                ("ED fn [FOR evt"),         # missing closing bracket
            )
        for test in tc:
            with self.assertRaises(ValueError, msg=test):
                tokens = parser.tokenize(test)
                parser._parse(tokens)


    def test_tokenizer_good(self):
        tc = (  # string                  # tokens
                ("abc def GHI klm",       ("abc","def","GHI","klm")),
                ("abc 'def GHI' klm",     ("abc","def GHI", "klm")),
                ("abc \"def GHI\" klm",   ("abc","def GHI", "klm")),
                ("abc '' klm",            ("abc","", "klm")),
                ("abc '''' klm",          ("abc","'", "klm")),
                ("abc [def] GHI",         ("abc","[","def","]","GHI")),
                ("abc [ def ] GHI",       ("abc","[","def","]","GHI")),
                ("abc [[def] GHI]",       ("abc","[","[","def","]","GHI","]")),
                ("abc [def]...",          ("abc","[","def","]","...")),
                ("abc [def...]",          ("abc","[","def","...","]")),
                ("abc... def GHI",        ("abc","...", "def","GHI")),
                ("",                      ()),
                ("!abc def",              ("!", "abc","def")),
                ("!!abc def",             ("!!", "abc","def")),
                ("@abc def",              ("@", "abc","def")),
                ("@@abc def",             ("@@", "abc","def")),
            )
        for test, expected in tc:
            self.assertSequenceEqual(parser.tokenize(test), expected, test)
        
    def test_tokenizer_bad(self):
        tc = (  # string   
                ("abc'def ghi' klm"),       # missing separator
                ("abc \"def ghi\"klm"),     # missing separator
                ("abc \"de"),               # missing closing quote
                ("abc 'de"),                # missing closing quote
                ("abc 'de\""),              # unbalanced quotes
            )
        for test in tc:
            with self.assertRaises(ValueError, msg=test):
                parser.tokenize(test)

    def test_unify_good(self):
        tc = ( # Pattern            # String            # Expected
             ("SET k TO v",         "SET KEY TO 123",    {'k':'KEY','v':'123'}),
             ("SET k TO v",         "set KEY To 123",    {'k':'KEY','v':'123'}),
             ("SET k TO v",         "SET Key TO 123",    {'k':'Key','v':'123'}),
            )

        for pattern, stmt, expected in tc:
            self.assertEqual(parser.unify(pattern, stmt), expected, pattern)

    def test_unify_quantifiers(self):
        tc = ( # Pattern            # String            # Expected
             ("SET k [TO] v",       "SET KEY TO 123",    {'k':'KEY','v':'123'}),
             ("SET k [TO] v",       "set KEY 123",       {'k':'KEY','v':'123'}),
             ("SET k [v]",          "SET Key 123",       {'k':'Key','v':'123'}),
             ("SET k [v]",          "SET Key",           {'k':'Key'}),
             ("SET k [v]...",       "SET Key",           {'k':'Key'}),
             ("SET k [v]...",       "SET Key 1",         {'k':'Key','v':['1']}),
             ("SET k [v]...",       "SET Key 1 2",       {'k':'Key','v':['1','2']}),
            )

        for pattern, stmt, expected in tc:
            self.assertEqual(parser.unify(pattern, stmt), expected, pattern)

    def test_unify_bad(self):
        tc = ( # Pattern            # String        
             ("SET :k TO :k",       "SET KEY TO 123"),
            )

        for pattern, stmt in tc:
            self.assertIsNone(parser.unify(pattern, stmt), pattern)
        
    def test_compile(self):
        tc = (
                ("abc def GHI klm",         ("abc","def","GHI","klm")),
            )

        for test, expected in tc:
            self.assertSequenceEqual(parser.compile(test)._pattern, expected, test)
