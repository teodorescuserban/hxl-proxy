insert into Users (user_id, email, name, name_given, name_family, last_login)
values
('user1', 'user1@example.org', 'User One', 'User', 'One', '2015-11-11 11:00:00'),
('user2', 'user2@example.org', 'User Two', 'User', 'Two', '2016-11-11 11:00:00');

insert into Recipes (recipe_id, user_id, name, url, schema_url, description, cloneable, stub, args, date_created, date_modified)
values
('AAAAA', 'user1', 'Recipe #1', 'http://example.org/basic-dataset.csv', 'http://example.org/schema.csv', 'First test recipe', 1, 'recipe1', '{}', '2015-11-11 11:00:00', '2015-11-11 11:00:00'),
('BBBBB', 'user2', 'Recipe #2', 'http://example.org/data.csv', null, null, 0, null, '{}', '2016-11-11 11:00:00', '2016-11-11 11:00:00');