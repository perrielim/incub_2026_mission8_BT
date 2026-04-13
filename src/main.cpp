#include <behaviortree_cpp/bt_factory.h>
#include <behaviortree_cpp/loggers/groot2_publisher.h>
#include <behaviortree_cpp/loggers/bt_cout_logger.h>
#include <behaviortree_cpp/loggers/bt_observer.h>
#include <chrono>
#include <iostream>
#include <thread>

void RegisterAllNodes(BT::BehaviorTreeFactory &factory);

int main()
{
    BT::BehaviorTreeFactory factory;
    RegisterAllNodes(factory);

    auto tree = factory.createTreeFromFile("generated/main_mission.xml");

    BT::StdCoutLogger logger(tree);
    BT::Groot2Publisher publisher(tree, 1667);

    auto root = tree.rootNode();
    for (int i = 0; i < 50; ++i)
    {
        auto status = root->executeTick();
        if (status == BT::NodeStatus::SUCCESS || status == BT::NodeStatus::FAILURE)
        {
            std::cout << "Tree finished with status: "
                      << BT::toStr(status) << std::endl;
            break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    return 0;
}