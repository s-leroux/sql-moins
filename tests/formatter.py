import unittest

from sqlm.formatter import *

class PEP249:
    # Dummy PEP-249 type objects
    # http://legacy.python.org/dev/peps/pep-0249/#type-objects
    class STRING:
        pass

    class BINARY:
        pass

    class NUMBER:
        pass

    class DATETIME:
        pass

    class ROWID:
        pass
    
# Dummy PEP-249 cursor attributes
# http://legacy.python.org/dev/peps/pep-0249/#cursor-attributes
PEP249_NUMBER_10 = ('N', PEP249.NUMBER, 11, 22, 10, 0, 1)
PEP249_NUMBER_14_2 = ('D', PEP249.NUMBER, 18, 22, 14, 2, 1)
PEP249_VARCHAR_20 = ('V', PEP249.STRING, 20, 20, 0, 0, 1)
PEP249_DATE = ('D', PEP249.DATETIME, 23, 7, 0, 0, 1)

class ColumnTestCase(unittest.TestCase):

    def test_VARCHAR_column(self):
        col = Column(*PEP249_VARCHAR_20)
        self.assertEqual(col.name, 'V')
        self.assertEqual(col.type_code, 'STRING')
        self.assertFalse(col.isNumber())
        self.assertEqual(col.align, '<')
        self.assertEqual(col.display_size, 20)
        self.assertEqual(col.getFormat(), '{!s:<20}')
        self.assertEqual(col.blank(), 20*'-')

    def test_NUMBER_column(self):
        col = Column(*PEP249_NUMBER_10)
        self.assertEqual(col.name, 'N')
        self.assertEqual(col.type_code, 'NUMBER')
        self.assertTrue(col.isNumber())
        self.assertEqual(col.align, '>')
        self.assertEqual(col.display_size, 11) # 10 + 1 for sign
        self.assertEqual(col.blank('*'), 11*'*')

    def test_DECIMAL_column(self):
        col = Column(*PEP249_NUMBER_14_2)
        self.assertEqual(col.name, 'D')
        self.assertEqual(col.type_code, 'NUMBER')
        self.assertTrue(col.isNumber())
        self.assertEqual(col.align, '>')
        self.assertEqual(col.display_size, 18) # 14 + 1 for sign 
                                               #    + 1 for dot 
                                               #    + 2 decimal places
        self.assertEqual(col.blank('-+-+'), '-+-+-+-+-+-+-+-+-+')
        #                                    01234567890123456789
        

    def test_make_column(self):
        cd = (PEP249_NUMBER_10, PEP249_VARCHAR_20)
        cl = make_columns(cd)

        self.assertEqual(len(cd), len(cl))
        self.assertEqual(cl[0].name, cd[0][0])
        self.assertEqual(cl[1].name, cd[1][0])

class PageTestCase(unittest.TestCase):
    def test_page(self):
        colA = Column(*PEP249_NUMBER_10)
        colB = Column(*PEP249_NUMBER_10)
        colC = Column(*PEP249_VARCHAR_20)

        page = Page([colA,colB, colC])

        self.assertIs(page.columns[0], colA)
        self.assertIs(page.columns[1], colB)
        self.assertIs(page.columns[2], colC)

        rows = [['1.3', '1.5', 'a'],
                ['101', '1.4', 'abc'],
                ['.33', '2.5', 'ab']]

        for row in rows:
            page.append(row)

        self.assertEqual(page.rows[0], rows[0])
        self.assertEqual(page.rows[1], rows[1])
        self.assertEqual(page.rows[2], rows[2])

        self.assertEqual(page.formats(), ['+999.99', '+9.9', 'XXX'])


class ToCharTestCase(unittest.TestCase):
    def test_to_char_null_format(self):
        din = "abc"
        dout = to_char(din, '')
        # empty format returns the empty string
        self.assertEqual(dout, '')

    def test_to_char_string(self):
        tests = [["abcdef", "XXXXXX", "abcdef"],
                 ["abcdef", "XXX", "abc"],
                 ["abcdef", "XXXXXXXXX", "   abcdef"]]

        for data, fmt, expected in tests:
            result = to_char(data,fmt)
            self.assertEqual(expected, result)

    def test_to_char_number(self):
        tests = [[ '+123',  "99999", "   123"],
                 [ '-123', "-99999", "  -123"],
                 [ '+123', "-99999", "  +123"],
                 [ '123.4', "99999.99", "   123.40"],
                 [ '12345', "99.99", "######"],
                 [ '123.44', "999.9", " 123.4"],
                 [ '123.456', "999.9", " 123.5"],
                 [ '123456789', "999,999,999", " 123,456,789"],
                 [ '0.456', '.99', " .46"],
                 [ '123.456', '999.', " 123."]]

        for data, fmt, expected in tests:
            result = to_char(data,fmt)
            self.assertEqual(expected, result)


class DecimalTestCase(unittest.TestCase):
    def test_decimal_tuple(self):
        tests = [[ '0.0001', (), (0,0,0,1)],
                 [ '2E-4',   (), (0,0,0,2)],
                 [ '123.456', (1,2,3), (4,5,6)],
                 [ '123', (1,2,3), ()]]

        for data, expected_integral, expected_fractional in tests:
            sign, integral, fractional = decimal_tuple(Decimal(data))
            self.assertEqual(expected_integral, integral, 'while testing '+data)
            self.assertEqual(expected_fractional, fractional, 'while testing '+data)

