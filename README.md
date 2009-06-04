#pyhaml

pyhaml is a port of [Haml](http://haml.hamptoncatlin.com), an HTML templating engine used primarily with Ruby on Rails.

The goals of the project are to create a Haml templating engine that is

1. pythonic
2. flexible
3. portable

#pythonic

In order to make haml a bit more pythonic, most of the syntax evaluated as Ruby is evaluated as python.

For example, the following Ruby Haml code snippet:

    %tagname{:attr1 => 'value1', :attr2 => 'value2'} Contents

is written in pyhaml as:

    %tagname{ 'attr1': 'value1', 'attr2': 'value2' } Contents

using python `dict` syntax rather than Ruby hash syntax.
