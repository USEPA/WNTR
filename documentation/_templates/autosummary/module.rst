{{ fullname | escape | underline}}

.. automodule:: {{ fullname }}
   :exclude-members: {% for item in attributes %}{{ item }}, {% endfor %}{% for item in functions %}{{ item }}, {% endfor %}{% for item in classes %}{{ item }}, {% endfor %}{% for item in exceptions %}{{ item }}, {% endfor %}

   {% block attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Module Attributes') }}

   .. autosummary::
      :toctree:
      :template: autosummary/base.rst
   {% for item in attributes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if functions %}
   .. rubric:: {{ _('Functions') }}

   .. autosummary::
      :nosignatures:
      :toctree:
      :template: autosummary/base.rst
   {% for item in functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if classes %}
   .. rubric:: {{ _('Classes') }}

   .. autosummary::
      :nosignatures:
      :toctree:
      :template: autosummary/class.rst
   {% for item in classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: {{ _('Exceptions') }}

   .. autosummary::
      :nosignatures:
      :toctree:
      :template: autosummary/exception.rst
   {% for item in exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

{% block modules %}
{% if modules %}
.. rubric:: Modules

.. autosummary::
   :toctree:
   :recursive:
   :template: autosummary/module.rst
{% for item in modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
