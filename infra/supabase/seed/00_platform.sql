-- Platform module registry (Doc 08 §6.1 + optional modules)
INSERT INTO module_definitions (id, name, module_class, description, dependencies) VALUES
-- Platform Core (auto-included for every Business)
('core-business-identity', 'Business Identity', 'platform_core', 'Business root entity and lifecycle', '{}'),
('core-business-profile', 'Business Profile', 'platform_core', 'Public-facing business profile', '{core-business-identity}'),
('core-website', 'Website', 'platform_core', 'Structured website model', '{core-business-profile}'),
('core-workspace', 'Workspace Foundation', 'platform_core', 'Operator shell foundation', '{core-business-identity}'),
('core-settings', 'Settings', 'platform_core', 'Business-wide configuration', '{core-business-identity}'),
('core-locations', 'Location Foundation', 'platform_core', 'Location management', '{core-business-identity}'),
('core-team-access', 'Team & Access', 'platform_core', 'Memberships, roles, permissions', '{core-business-identity}'),
('core-module-management', 'Module Management', 'platform_core', 'Module registry and lifecycle', '{core-business-identity}'),
('core-notifications', 'Basic Notifications', 'platform_core', 'In-platform notifications', '{core-business-identity}'),
('core-marketplace-presence', 'Marketplace Presence', 'platform_core', 'Marketplace indexing projection', '{core-business-profile}'),
-- Optional Business Modules (First Launch)
('offerings-catalog', 'Offerings Catalog', 'optional', 'Product/service catalog', '{core-business-profile}'),
('orders', 'Orders', 'optional', 'Order management', '{offerings-catalog}'),
('bookings', 'Bookings', 'optional', 'Reservation management', '{offerings-catalog}'),
('payments', 'Payments', 'optional', 'Payment processing', '{orders}'),
('memberships', 'Memberships', 'optional', 'Membership plans', '{payments}'),
('customer-relationships', 'Customer Relationships', 'optional', 'CRM', '{orders}'),
('leads', 'Leads', 'optional', 'Lead pipeline', '{core-business-profile}'),
('inventory', 'Inventory', 'optional', 'Stock management', '{offerings-catalog}'),
('fulfilment', 'Fulfilment', 'optional', 'Delivery and pickup', '{orders,inventory}'),
('workforce', 'Workforce', 'optional', 'Staff and provider management', '{core-team-access}')
ON CONFLICT (id) DO NOTHING;
