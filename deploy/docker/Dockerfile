FROM odoo:18.0

USER root

# Copy enterprise and custom addons into the image
COPY ./enterprise /mnt/enterprise-addons
COPY ./custom-addons /mnt/custom-addons

# Ensure proper ownership
RUN chown -R odoo:odoo /mnt/enterprise-addons /mnt/custom-addons

USER odoo
