pragma foreign_keys='on';

drop table if exists Users;

create table Users (
       user_id varchar(128) primary key,
       email varchar(128) not null,
       name varchar(128) not null,
       name_given varchar(64),
       name_family varchar(64),
       last_login datetime not null
);

