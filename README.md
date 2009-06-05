#pyHaml

pyHaml is a python port of [Haml](http://haml.hamptoncatlin.com), an HTML templating engine used primarily with Ruby on Rails.
I'll refer to Ruby Haml as rHaml.

The goals of the project are to create a Haml templating engine that is

1. pythonic
2. flexible
3. portable

#pythonic

In order to make pyHaml a bit more pythonic, most of the syntax evaluated as Ruby in rHaml is evaluated as python.

For example, the following rHaml code snippet:

    %tagname{:attr1 => 'value1', :attr2 => 'value2'} Contents

is written in pyhaml as:

    %tagname{'attr1': 'value1', 'attr2': 'value2'} Contents

using python `dict` syntax rather than Ruby hash syntax.

#flexible

pyHaml aims to be flexible and intuitive, allowing python to be evaluated inline as would be expected.

    - def foo(i):
      %p = i ** 2
    - for i in range(4):
      - foo(i)

yields

    <p>0</p>
    <p>1</p>
    <p>4</p>
    <p>9</p>

#portable

pyHaml aims to run on both version 2.x and 3.x of python is a maintenance friendly manner.
This is accomplished by monkey patching python upon starting execution.
