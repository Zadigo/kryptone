import json

from kryptone.db.constraints import MaxLengthConstraint


class Field:
    python_type = str
    base_validators = []
    base_constraints = []

    def __init__(self, name, *, max_length=None, null=False, primary_key=False, default=None, unique=False, validators=[]):
        self.name = name
        self.null = null
        self.primary_key = primary_key
        self.default = default
        self.unique = unique
        self.table = None
        self.max_length = max_length
        self.base_validators = self.base_validators + validators
        self.base_field_parameters = {
            'primary key': False,
            'null': False,
            'not null': True,
            'unique': False
        }
        # self.base_field_parameters = [self.field_type, 'not null']

        if max_length is not None:
            instance = MaxLengthConstraint(fields=[name])
            self.base_constraints.append(instance)

    def __repr__(self):
        return f'<{self.__class__.__name__}[{self.name}]>'

    def __hash__(self):
        return hash((self.name))

    def __eq__(self, value):
        if isinstance(value, Field):
            return value.name == self.name
        return self.name == value

    @property
    def field_type(self):
        return 'text'

    @classmethod
    def create(cls, name, params):
        instance = cls(name)
        instance.base_field_parameters = params
        if 'null' in params:
            instance.null = True

        if 'primary key' in params:
            instance.primary_key = True
        instance.field_parameters()
        return instance

    def to_python(self, data):
        return self.python_type(data)

    def to_database(self, data):
        if callable(data):
            return self.python_type(str(data()))
        
        if data is None:
            return ''
        
        if not isinstance(data, self.python_type):
            raise ValueError(
                f"{type(data)} should be an instance "
                f"of {self.python_type}"
            )
        return self.python_type(data)

    def field_parameters(self):
        """Adapt the python function parameters to the
        database field creation paramters

        >>> Field('visited', default=False)
        ... ['visited', 'text', 'not null', 'default', 0]
        """
        field_type = None
        if self.max_length is not None:
            field_type = f'varchar({self.max_length})'
            
        initial_parameters = [self.name, field_type or self.field_type]

        if self.null:
            self.base_field_parameters['null'] = True
            self.base_field_parameters['not null'] = False
        else:
            self.base_field_parameters['null'] = False
            self.base_field_parameters['not null'] = True

        self.base_field_parameters['primary key'] = self.primary_key
        self.base_field_parameters['unique'] = self.unique

        if self.default is not None:
            database_value = self.to_database(self.default)
            value = self.table.backend.quote_value(database_value)
            initial_parameters.extend(['default', value])

        true_parameters = list(filter(lambda x: x[1] is True, self.base_field_parameters.items()))
        additional_parameters = list(map(lambda x: x[0], true_parameters))
        base_field_parameters = initial_parameters + additional_parameters
        return base_field_parameters

        # base_parameters = self.base_field_parameters.copy()
        # if self.null:
        #     base_parameters.pop(base_parameters.index('not null'))
        #     base_parameters.append('null')

        # if self.primary_key:
        #     base_parameters.append('primary key')

        # if self.default is not None:
        #     database_value = self.to_database(self.default)
        #     value = self.table.backend.quote_value(database_value)
        #     base_parameters.extend(['default', value])

        # if self.unique:
        #     base_parameters.append('unique')
        #     if 'not null' not in base_parameters and 'null' in base_parameters:
        #         base_parameters.index(
        #             'not null', base_parameters.index('null'))

        # base_parameters.insert(0, self.name)
        # self.base_field_parameters = base_parameters
        # return base_parameters

    def prepare(self, table):
        from kryptone.db.tables import Table
        if not isinstance(table, Table):
            raise ValueError(f"{table} should be an instance of Table")
        self.table = table

    def deconstruct(self):
        return (self.name, self.field_parameters())


class CharField(Field):
    pass


class IntegerField(Field):
    python_type = int

    def __init__(self, name, *, min_value=None, max_value=None, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(name, **kwargs)

    @property
    def field_type(self):
        return 'integer'


class JSONField(Field):
    python_type = dict

    def to_python(self, data):
        return json.loads(data)

    def to_database(self, data):
        return json.dumps(data, ensure_ascii=False, sort_keys=True)


class BooleanField(Field):
    truth_types = ['true', 't', 1, '1']
    false_types = ['false', 'f', 0, '0']

    def to_python(self, data):
        if data in self.truth_types:
            return True

        if data in self.false_types:
            return False

    def to_database(self, data):
        if isinstance(data, bool):
            if data == True:
                return 1
            return 0

        if isinstance(data, str):
            if data in self.truth_types:
                return 1

            if data in self.false_types:
                return 0
        return data


class AutoField(IntegerField):
    """Represents an alias to the `rowid` field
    in the database"""

    def __init__(self):
        super().__init__('id', primary_key=True)
        self.base_field_parameters.pop('null')
        self.base_field_parameters.pop('not null')
        self.base_field_parameters['autoincrement'] = True
