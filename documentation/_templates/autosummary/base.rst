{% if objtype == 'property' %}
:orphan:
{% endif %}

{{ objname | escape | underline}}

.. rubric:: *module* :mod:`{{ module }}`

.. currentmodule:: {{ module }}

{% if objtype == 'property' %}
property
{% endif %}

.. auto{{ objtype }}:: {{ fullname | replace(module + ".", module + "::") }}
