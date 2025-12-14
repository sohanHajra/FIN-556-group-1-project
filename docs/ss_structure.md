# go_strategies.sh — quickly jump to the StrategyStudio strategies directory

cd ~/ss/sdk/RCM/StrategyStudio/examples/strategies

/ss/bt/backtester_config.txt pint to text tick files

go to ss prefferred feeds go in and there and add entry for nasdaq


/ss/bt/preferred_feeds.csv add nasdaq



----

# work on auto strat builder


# clone_strategy.sh — duplicates dia_index_arb_strategy to acharov2_strategy

# and updates Makefile entries accordingly


# Step 1: go to strategies directory

cd ~/ss/sdk/RCM/StrategyStudio/examples/strategies/ || {

  echo "Directory not found!"

  exit 1

}


# Step 2: copy the strategy folder

cp -r dia_index_arb_strategy acharov2_strategy


# Step 3: enter new folder

cd acharov2_strategy/ || {

  echo "❌ Failed to enter acharov2_strategy directory"

  exit 1

}


# Step 4: rename files

mv DiaIndexArb.h acharov2_strategy.h

mv DiaIndexArb.cpp acharov2_strategy.cpp

mv DiaIndexArb.so acharov2_strategy.so


# Step 5: update Makefile

if [ -f Makefile ]; then

  echo "Updating Makefile..."

  sed -i.bak \

    -e 's|LIBRARY=.*|LIBRARY=acharov2_strategy.so|' \

    -e 's|SOURCES=.*|SOURCES=acharov2_strategy.cpp|' \

    -e 's|HEADERS=.*|HEADERS=acharov2_strategy.h|' \

    Makefile

  echo "Makefile updated (backup saved as Makefile.bak)"

else

  echo "No Makefile found in directory!"

fi


echo "Successfully cloned DiaIndexArb strategy to acharov2_strategy"