import unittest

import sqlm.utils as utils

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
            self.assertEqual(utils._unquote(test), expected, test)

    def test_tokenizer_good(self):
        tc = (  # string                    # tokens
                ("abc def GHI klm",         ("abc","def","GHI","klm")),
                ("abc 'def GHI' klm",       ("abc","def GHI", "klm")),
                ("abc \"def GHI\" klm",     ("abc","def GHI", "klm")),
                ("abc '' klm",              ("abc","", "klm")),
                ("abc '''' klm",            ("abc","'", "klm")),
                ("",                        ()),
                ("!abc def",                ("!", "abc","def")),
                ("!!abc def",               ("!!", "abc","def")),
                ("@abc def",                ("@", "abc","def")),
                ("@@abc def",               ("@@", "abc","def")),
            )
        for test, expected in tc:
            self.assertSequenceEqual(utils.tokenize(test), expected, test)
        
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
                utils.tokenize(test)


    def test_unify_good(self):
        tc = ( # Pattern            # String            # Expected
             ("SET k TO v",         "SET KEY TO 123",    {'k':'KEY','v':'123'}),
             ("SET k TO v",         "set KEY To 123",    {'k':'KEY','v':'123'}),
             ("SET k TO v",         "SET Key TO 123",    {'k':'Key','v':'123'}),
             ("SET k TO k",         "SET KEY TO KEY",    {'k':'KEY'}),
            )

        for pattern, stmt, expected in tc:
            self.assertEqual(utils.unify(pattern, stmt), expected, pattern)

    def test_unify_bad(self):
        tc = ( # Pattern            # String        
             ("SET :k TO :k",       "SET KEY TO 123"),
            )

        for pattern, stmt in tc:
            with self.assertRaises(ValueError, msg=pattern):
                utils.unify(pattern, stmt)
        
    def test_compile(self):
        tc = (
                ("abc def GHI klm",         ("abc","def","GHI","klm")),
            )

        for test, expected in tc:
            self.assertSequenceEqual(utils.compile(test)._tokens, expected, test)
