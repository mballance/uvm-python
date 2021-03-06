
import unittest
from uvm.reg.uvm_reg import UVMReg
from uvm.reg.uvm_reg_field import UVMRegField


class TestUVMReg(unittest.TestCase):

    def setUp(self):
        pass

    def create_reg(self, name='reg', nbits=32):
        reg = UVMReg(name, nbits, False)
        for i in range(0, nbits):
            f1 = UVMRegField('my_field_' + str(i))
            f1.configure(reg, 1, i, 'RW', volatile=False, reset=i % 2, has_reset=True,
                    is_rand=False, individually_accessible=True)
        return reg

    def test_add_field(self):
        UVMRegField.define_access('RW')
        reg = UVMReg('my_reg', 32, False)
        f1 = UVMRegField('my_field_1')
        f1.configure(reg, 16, 0, 'RW', volatile=False, reset=0, has_reset=True,
                is_rand=False, individually_accessible=True)
        arr = []
        reg.get_fields(arr)
        print(str(reg.m_fields))
        self.assertEqual(len(arr), 1)

    def test_base_ops(self):
        UVMRegField.define_access('RW')
        reg32 = self.create_reg('reg_32', 32)
        arr = []
        reg32.get_fields(arr)
        self.assertEqual(len(arr), 32)
        self.assertEqual(reg32.predict(0), True)
        # Why does not fail self.assertEqual(reg32.predict(1234), False)
        self.assertEqual(reg32.get(), 0)
        reg32.set(0x12345678)
        val = reg32.get()
        self.assertEqual(val, 0x12345678)


if __name__ == '__main__':
    unittest.main()
