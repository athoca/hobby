# Doc: https://docs.sqlalchemy.org/en/13/orm/tutorial.html
import sqlalchemy
sqlalchemy.__version__

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, SmallInteger, BigInteger
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# Because BigInteger not auto-incremetal as primary-key in sqlite, but others
from sqlalchemy.dialects import postgresql, mysql, sqlite
BigIntegerType = BigInteger()
BigIntegerType = BigIntegerType.with_variant(postgresql.BIGINT(), 'postgresql')
BigIntegerType = BigIntegerType.with_variant(mysql.BIGINT(), 'mysql')
BigIntegerType = BigIntegerType.with_variant(sqlite.INTEGER(), 'sqlite')

class EKUser(Base):
    __tablename__ = 'ek_users'
    id = Column(Integer, primary_key=True, autoincrement=False)  # ebayK user Id
    name = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False)
    active_date = Column(DateTime, nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)

    def _get_url(self):
        return "https://www.ebay-kleinanzeigen.de/s-bestandsliste.html?userId={}".format(self.id)

    def __repr__(self):
        return "<EKUser(id={}, name={}, active from {})> \n  url: {}".format(self.id, self.name, self.active_date, self._get_url())

class EKItem(Base):
    __tablename__ = 'ek_items'
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    title = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    release_date = Column(DateTime, nullable=False)
    stadt = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False)
    sub_category = Column(String(255), nullable=False)
    status = Column(String(30), nullable=True)
    description =Column(Text, nullable=True)
    image_nb = Column(Integer, nullable=True)
    image_label = Column(String(255), nullable=True)
    seller_id = Column(Integer, ForeignKey('ek_users.id'))
    seller = relationship("EKUser", back_populates="items")

    def _get_url(self):
        return "https://www.ebay-kleinanzeigen.de/s-anzeige/{}".format(self.id)

    def __repr__(self):
        return "<EKItem(id={}, title={}, status={})> \n  url: {}".format(self.id, self.title, self.status, self._get_url())

EKUser.items = relationship("EKItem", order_by=EKItem.id, back_populates="seller")

class EKViewCount(Base):
    __tablename__ = 'ek_view_counts'
    id = Column(BigIntegerType, primary_key=True)    
    count = Column(SmallInteger, nullable=False)
    at = Column(Integer, nullable=False)   # each 1 minute is 1 increment
    item_id = Column(BigInteger, ForeignKey('ek_items.id'), nullable=False)

    def __repr__(self):
        return "<EKViewCount(of item={}, count={}, at={})>".format(self.item_id, self.count, self.at)

# temporary to transfer data, do not need ForeignKey
class EKMonitoringItem(Base):
    __tablename__ = 'ek_monitoring_items'
    id = Column(BigIntegerType, primary_key=True)   
    item_id = Column(BigInteger, nullable=False)
    seller_id = Column(Integer, nullable=False)
    next_count_time = Column(DateTime, nullable=False)
    count_duration = Column(Integer, nullable=False)

    def __repr__(self):
        return "<EKMonitoringItem(item_id={}, seller_id={})>".format(self.item_id, self.seller_id)

from sqlalchemy import create_engine
engine = create_engine('sqlite:////Users/chaunguyen/workspace/hobby/alphaone/alphaone.db', echo=True)

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
session = Session()