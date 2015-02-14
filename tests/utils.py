import unittest

from sqlm.utils import tokenize, _unquote, unify

class TokenizerTestCase(unittest.TestCase):
    def test_unquote(self):
        """Test unquoted representation of tokens.
        """
        tc = (  # token                     # canonical representation
                ("abc"                      , "ABC"),
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
            self.assertEqual(_unquote(test), expected, test)

    def test_tokenizer_good(self):
        tc = (  # string                    # tokens
                ("abc def ghi klm",         ("ABC","DEF","GHI","KLM")),
                ("abc 'def ghi' klm",       ("ABC","def ghi", "KLM")),
                ("abc \"def ghi\" klm",     ("ABC","def ghi", "KLM")),
                ("abc '' klm",              ("ABC","", "KLM")),
                ("abc '''' klm",            ("ABC","'", "KLM")),
                ("",                        ()),
            )
        for test, expected in tc:
            self.assertSequenceEqual(tokenize(test), expected, test)
        
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
                tokenize(test)


    def test_unify_good(self):
        tc = ( # Pattern            # String            # Expected
             ("SET :k TO :v",       "SET KEY TO 123",    {'K':'KEY','V':'123'}),
             ("SET :k TO :k",       "SET KEY TO KEY",    {'K':'KEY'}),
            )

        for pattern, stmt, expected in tc:
            self.assertEqual(unify(pattern, stmt), expected, pattern)

    def test_unify_bad(self):
        tc = ( # Pattern            # String        
             ("SET :k TO :k",       "SET KEY TO 123"),
            )

        for pattern, stmt in tc:
            with self.assertRaises(ValueError, msg=pattern):
                unify(pattern, stmt)
        

