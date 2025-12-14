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


-----

Extra notes:

cd ~/ss/sdk/RCM/StrategyStudio/examples/strategies/
cp -r dia_index_arb_strategy acharov2_strategy
cd acharov2_strategy/
mv DiaIndexArb.h acharov2_strategy.h
mv DiaIndexArb.cpp acharov2_strategy.cpp
mv DiaIndexArb.so acharov2_strategy.so

-- in nano Makefile rename
LIBRARY=acharov2_strategy.so, SOURCES=acharov2_strategy.cpp, HEADERS=acharov2_strategy.h

~/ss/bt/StrategyServerBacktesting

----

make copy_strategy

change in acharov2_strategy.cpp 
-> include header to acharov2_strategy.h

Strategy exports in acharov2_strategy.h
on return 

make copy_strategy

(in bt directory)
./StrategyServerBacktesting &


---- create instance ----

cd "$HOME/ss/bt/utilities" && ./StrategyCommandLine cmd create_instance MyAcharov2Instance acharov2_strategy UIUC SIM-1001-101 dlariviere 9900000 -symbols "SPY|NVDA|GOOG"

---- start back test ----

cd "$HOME/ss/bt/utilities" && ./StrategyCommandLine cmd start_backtest "$startDate" "$endDate" "$instanceName" 0


cd "$HOME/ss/bt/utilities" && ./StrategyCommandLine cmd start_backtest "2023-09-05" "2023-09-05" "MyAcharov2Instance" 0

---- see running strategies ----

cd "$HOME/ss/bt/utilities" && ./StrategyCommandLine cmd strategy_instance_list

---- termination for strategies

cd "$HOME/ss/bt/utilities" && ./StrategyCommandLine cmd 
terminate|pause|stop -all

--- see results ---

ls -lA ~/ss/bt/backtesting-results/

--- export results ---
cd "$HOME/ss/bt/utilities" && ./StrategyCommandLine cmd export_cra_file "~/ss/bt/backtesting-results/BACK_MyAcharov2Instance_2025-10-22_031417_start_09-05-2023_end_09-05-2023.cra"


--- for corrupted strategies, run

make clean

make

make copy_strategy

***don't worry about warning***


--- helper script

/vagrant/provision_scripts/run_backtest.sh




cd "$HOME/ss/bt/utilities" && ./StrategyCommandLine cmd export_cra_file "/home/ach
arov2/ss/bt/backtesting-results/BACK_MyAcharov2Instance_2025-10-22_031417_start_09-05-2023_end_09-05-2023.cra"